# src/services/ai/openai_client.py
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Tuple

import httpx
from openai import AsyncOpenAI

from src.config import config

# Модулярный singleton для переиспользования соединений
_client: Optional[AsyncOpenAI] = None
_httpx_client: Optional[httpx.AsyncClient] = None
_client_lock = asyncio.Lock()


async def get_openai_client() -> Tuple[AsyncOpenAI, Optional[httpx.AsyncClient]]:
    """
    Ленивая инициализация AsyncOpenAI.
    Возвращает пару (client, httpx_client), чтобы можно было корректно закрыть httpx при остановке приложения.
    """
    global _client, _httpx_client

    if _client is not None:
        return _client, _httpx_client

    async with _client_lock:
        if _client is None:
            if config.ai.proxy_url:
                _httpx_client = httpx.AsyncClient(
                    proxy=config.ai.proxy_url,
                    timeout=httpx.Timeout(30.0, connect=10.0),
                )
                _client = AsyncOpenAI(
                    api_key=config.ai.openai_api_key.get_secret_value(),
                    http_client=_httpx_client,
                )
            else:
                _client = AsyncOpenAI(
                    api_key=config.ai.openai_api_key.get_secret_value()
                )

    return _client, _httpx_client


async def close_openai_client() -> None:
    """Аккуратно закрыть httpx-клиент, если он создавался (например, при остановке сервиса/воркера)."""
    global _client, _httpx_client
    if _httpx_client is not None:
        await _httpx_client.aclose()
    _client = None
    _httpx_client = None


async def chat_complete(
    messages: List[Dict[str, str]],
    *,
    model: str = "gpt-5-mini",
    # temperature: float = 0.2,
    max_tokens: Optional[int] = None,
    **kwargs: Any,
) -> str:
    """
    Универсальная обёртка над Chat Completions.
    Возвращает только текст первого сообщения (content), чтобы было удобно использовать в сервисах.
    """
    client, _ = await get_openai_client()

    resp = await client.chat.completions.create(
        model=model,
        messages=messages,
        # temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )

    return resp.choices[0].message.content or ""
