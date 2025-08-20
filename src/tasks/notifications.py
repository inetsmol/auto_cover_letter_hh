# src/tasks/notifications.py
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
)

from src.config import config

logger = logging.getLogger(__name__)


async def _send_message(chat_id: int, text: str) -> None:
    """
    Отправка сообщения через краткоживущего бота, привязанного к текущему event loop.
    Не используем глобальный bot из src.bot_init, чтобы избежать конфликтов циклов.
    """
    async with Bot(token=config.bot.token.get_secret_value(), session=AiohttpSession()) as _bot:
        await _bot.send_message(chat_id=chat_id, text=text, disable_notification=True)


async def notification_task(user_id: int | str) -> None:
    """
    Отправляет простое тестовое уведомление пользователю в Telegram.
    Предполагается, что user_id == Telegram chat_id.
    """
    chat_id = int(user_id)
    text = "🔔 Тестовое уведомление: бот на связи! Если вы видите это сообщение — всё работает ✅"

    try:
        logger.info("Sending notification to user_id=%s", chat_id)
        await _send_message(chat_id, text)

    except TelegramRetryAfter as e:
        # Достигли лимита Telegram — ждём и пробуем ещё раз.
        logger.warning("Rate limit when notifying %s. Retry after %s sec.", chat_id, e.retry_after)
        await asyncio.sleep(e.retry_after)
        try:
            await _send_message(chat_id, text)
            logger.info("Notification sent on retry to user_id=%s", chat_id)
        except Exception as e2:
            logger.exception("Second attempt failed for user_id=%s: %s", chat_id, e2)

    except TelegramForbiddenError:
        # Пользователь заблокировал бота или не нажимал /start
        logger.warning("Cannot send to user_id=%s: bot blocked or user hasn't started the bot.", chat_id)

    except (TelegramBadRequest, TelegramNetworkError) as e:
        logger.exception("Telegram API/network error while notifying user_id=%s: %s", chat_id, e)

    except Exception as e:
        logger.exception("Unexpected error in notification_task for user_id=%s: %s", chat_id, e)
