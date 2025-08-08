# src/utils/asyncio_helpers.py

import asyncio
import contextlib
from typing import Any, Awaitable

def run_async(coro: Awaitable[Any]) -> Any:
    """
    Безопасно запускает корутину из синхронного контекста Celery.
    В Celery-процессах обычно нет активного event loop — используем asyncio.run.
    Если вдруг цикл уже существует и запущен (редко в Celery), создаём новый изолированный.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Избегаем nest_asyncio; создаём отдельный новый цикл
        new_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(new_loop)
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.run_until_complete(_shutdown_asyncgens_safely(new_loop))
            new_loop.close()
            asyncio.set_event_loop(loop)
    else:
        return asyncio.run(coro)


async def _shutdown_asyncgens_safely(loop: asyncio.AbstractEventLoop) -> None:
    # Корректное завершение асинхронных генераторов (для Python 3.10+ уже ок)
    tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
    for t in tasks:
        t.cancel()
    if tasks:
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.gather(*tasks)
