# src/services/ai/openai_client.py
from __future__ import annotations

"""
Тонкая async-обёртка над пулом OpenAI для совместимости со старым импортом.

Использование:
    from src.services.ai.openai_client import chat_complete
    text = await chat_complete(messages)
"""

from typing import Dict, List

from src.services.ai.openai_pool import chat_complete_async


async def chat_complete(messages: List[Dict[str, str]], *, model: str = "gpt-5-mini", **kwargs) -> str:
    """
    Асинхронный вызов Chat Completions.
    Делегирует в пул (долгоживущий httpx/AsyncOpenAI в фон.цикле Celery).
    """
    return await chat_complete_async(messages, model=model, **kwargs)




# from typing import Dict, List
#
# import httpx
# from openai import AsyncOpenAI
#
# from src.config import config
#
# api_key = config.ai.openai_api_key.get_secret_value()
# proxy_url = config.ai.proxy_url
#
#
# # Минимальная, но живучая обёртка
# async def chat_complete(messages: List[Dict[str, str]], timeout: float = 20.0,) -> str:
#     """
#     Минимальный async-вызов Chat Completions.
#     PROXY берётся из аргумента или из config.ai.proxy_url.
#     """
#
#     proxy = proxy_url if proxy_url is not None else (config.ai.proxy_url or None)
#
#     async with httpx.AsyncClient(
#         proxy=proxy,
#         timeout=httpx.Timeout(timeout, connect=min(10.0, timeout)),
#     ) as http:
#         client = AsyncOpenAI(
#             api_key=api_key,
#             http_client=http,
#         )
#         completion = await client.chat.completions.create(
#             model="gpt-5-mini",
#             messages=messages
#         )
#         return completion.choices[0].message.content
#
#
#
#     client = AsyncOpenAI(api_key=api_key) if proxy_url is None or proxy_url == "" else AsyncOpenAI(api_key=api_key, http_client=httpx.AsyncClient(proxy=proxy_url))
#     completion = await client.chat.completions.create(
#         model="gpt-5-mini",
#         messages=messages
#     )
#     return completion.choices[0].message.content
