
from __future__ import annotations

"""
Долгоживущий пул для OpenAI + httpx под Celery.

Ключевые идеи:
- Один фоновый event loop на процесс воркера (thread) → общий пул соединений httpx.
- Нормализованный proxy (пустые строки → None), современный параметр httpx `proxy=`.
- Разнесённые таймауты (connect/read/write/pool).
- Простой backoff для временных ошибок (429/таймаут/сеть/5xx).
"""

import asyncio
import threading
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

import httpx
from openai import AsyncOpenAI
from openai import APITimeoutError, RateLimitError, APIConnectionError, APIError


DEFAULT_MODEL = "gpt-5-mini"


@dataclass(frozen=True)
class OpenAISettings:
    """Настройки клиента OpenAI/httpx.
    Attributes:
        api_key: API-ключ OpenAI.
        proxy_url: URL прокси (или None). Пустые строки автоматически фильтруются.
        connect_timeout: Таймаут на установку соединения/CONNECT/TLS (сек).
        read_timeout: Таймаут ожидания ответа (сек).
        pool_timeout: Таймаут ожидания свободного соединения из пула (сек).
        http2: Включать ли HTTP/2.
    """
    api_key: str
    proxy_url: Optional[str] = None
    connect_timeout: float = 15.0
    read_timeout: float = 60.0
    pool_timeout: float = 60.0
    http2: bool = True


class _LoopThread:
    """Фоновый asyncio-цикл в отдельном потоке.

    Нужен, чтобы переиспользовать асинхронные httpx/AsyncOpenAI клиенты
    между задачами Celery, не создавая новый event loop каждый раз.
    """
    def __init__(self) -> None:
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        def _runner() -> None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._ready.set()
            self._loop.run_forever()
            # Аккуратно завершаем все таски перед закрытием цикла
            pending = asyncio.all_tasks(loop=self._loop)
            for t in pending:
                t.cancel()
            if pending:
                self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            self._loop.close()

        self._thread = threading.Thread(target=_runner, name="openai-loop", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=5)

    def stop(self) -> None:
        if not self._loop:
            return
        self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=10)

    def submit(self, coro: "asyncio.Future[Any] | asyncio.coroutines") -> Any:
        """Выполнить корутину в фоновом цикле и дождаться результата (блокирующе)."""
        if not self._loop:
            raise RuntimeError("Loop is not started")
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result()

    def submit_future(self, coro: "asyncio.Future[Any] | asyncio.coroutines"):
        """Выполнить корутину в фоновом цикле и вернуть concurrent.futures.Future.
        Это позволяет await'ить её из другого asyncio-цикла через asyncio.wrap_future().
        """
        if not self._loop:
            raise RuntimeError("Loop is not started")
        return asyncio.run_coroutine_threadsafe(coro, self._loop)


_loop = _LoopThread()


class _Clients:
    """Хранилище долгоживущих клиентов (на процесс)."""
    http: Optional[httpx.AsyncClient] = None
    ai: Optional[AsyncOpenAI] = None


_clients = _Clients()


def _normalize_proxy(url: Optional[str]) -> Optional[str]:
    """Пустые/пробельные строки → None, иначе возвращаем исходный URL."""
    if url and url.strip():
        return url.strip()
    return None


async def _ainit_clients(cfg: OpenAISettings) -> None:
    """Асинхронная инициализация httpx и OpenAI-клиента внутри фонового цикла."""
    proxy = _normalize_proxy(cfg.proxy_url)

    timeout = httpx.Timeout(
        # По умолчанию общий таймаут None (без лимита), задаём по фазам:
        None,
        connect=cfg.connect_timeout,
        read=cfg.read_timeout,
        write=cfg.read_timeout,
        pool=cfg.pool_timeout,
    )

    http = httpx.AsyncClient(
        http2=cfg.http2,
        timeout=timeout,
        proxy=proxy,  # NB: в httpx 0.27+ используем 'proxy=', а не 'proxies='
    )
    ai = AsyncOpenAI(api_key=cfg.api_key, http_client=http)

    _clients.http = http
    _clients.ai = ai


async def _aclose_clients() -> None:
    """Аккуратно закрываем клиентов (внутри фонового цикла)."""
    if _clients.http:
        try:
            await _clients.http.aclose()
        finally:
            _clients.http = None
    _clients.ai = None


def setup(settings: OpenAISettings) -> None:
    """Запуск фонового цикла и инициализация клиентов. Вызывать один раз на процесс."""
    _loop.start()
    _loop.submit(_ainit_clients(settings))


def teardown() -> None:
    """Закрыть клиентов и остановить фон.цикл. Вызывать при завершении процесса."""
    try:
        _loop.submit(_aclose_clients())
    finally:
        _loop.stop()


async def _achat_complete(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_MODEL,
    **kwargs: Any,
) -> str:
    """Асинхронный вызов Chat Completions в фоновом цикле с ретраями."""
    if not _clients.ai:
        raise RuntimeError("OpenAI client is not initialized")

    # Небольшой экспоненциальный backoff
    delays = (0.5, 1.0, 2.0, 4.0)
    last_err: Optional[BaseException] = None

    for delay in (*delays, None):
        try:
            resp = await _clients.ai.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs,
            )
            return resp.choices[0].message.content
        except (RateLimitError, APITimeoutError, APIConnectionError) as e:
            last_err = e
            if delay is None:
                raise
            await asyncio.sleep(delay)
        except APIError as e:
            # 5xx — ретраим; остальные — пробрасываем
            status = getattr(e, "status_code", 0) or 0
            if 500 <= status < 600 and delay is not None:
                last_err = e
                await asyncio.sleep(delay)
            else:
                raise
    assert last_err is not None
    raise last_err


def chat_complete_sync(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_MODEL,
    **kwargs: Any,
) -> str:
    """Синхронная обёртка — удобно для прямого вызова из кода без asyncio."""
    return _loop.submit(_achat_complete(messages, model=model, **kwargs))


async def chat_complete_async(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_MODEL,
    **kwargs: Any,
) -> str:
    """Асинхронная обёртка — удобно для вызова из async-кода (например, FastAPI)."""
    fut = _loop.submit_future(_achat_complete(messages, model=model, **kwargs))
    # оборачиваем concurrent.futures.Future в asyncio Future и дожидаемся результата
    return await asyncio.wrap_future(fut)
