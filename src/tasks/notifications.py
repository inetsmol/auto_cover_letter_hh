# src/tasks/notifications.py
from __future__ import annotations

import asyncio
import logging
from typing import Iterable, List, Sequence, Optional

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
)
from tortoise import timezone
from tortoise.expressions import Q

from src.config import config
from src.models import User, ApplicationResult

logger = logging.getLogger(__name__)


# Ограничим количество ссылок в одном сообщении, чтобы не упереться в лимит Telegram (4096 символов)
TEST_LINKS_LIMIT = 50


def _unique_preserve_order(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in items:
        if x is None:
            continue
        sx = str(x)
        if sx not in seen:
            seen.add(sx)
            out.append(sx)
    return out


def _build_message(max_total_vacancies: int, sent_sum: int, skipped_ids: Sequence[str]) -> str:
    if skipped_ids:
        links = [f"https://hh.ru/vacancy/{vid}" for vid in skipped_ids[:TEST_LINKS_LIMIT]]
        extra = len(skipped_ids) - len(links)
        links_block = "\n".join(links) + (f"\n… и ещё {extra} с тестами" if extra > 0 else "")
    else:
        links_block = "— нет"

    # Простое текстовое сообщение без parse_mode — Telegram сам превратит http-ссылки в кликабельные
    text = (
        "🔔 Отчёт по обработке вакансий\n\n"
        f"• Вакансий найдено (максимум за прогон): {max_total_vacancies}\n"
        f"• Отправлено откликов: {sent_sum}\n"
        "• Вакансии с тестами (отклик пропущен):\n"
        f"{links_block}"
    )
    return text


async def _send_message(chat_id: int, text: str) -> None:
    """
    Отправка сообщения через краткоживущего бота, привязанного к текущему event loop.
    Не используем глобальный bot из src.bot_init, чтобы избежать конфликтов циклов.
    """
    async with Bot(token=config.bot.token.get_secret_value(), session=AiohttpSession()) as _bot:
        await _bot.send_message(chat_id=chat_id, text=text, disable_notification=True)


async def _process_user(user_id: int) -> None:
    """
    Обработать одного пользователя:
      - взять все ApplicationResult с notified=False
      - посчитать max(total_vacancies), сумму sent_applications
      - собрать уникальные skipped_tests и отправить сообщение
      - пометить результаты как notified=True
    """
    # Выборка необработанных результатов
    results: List[ApplicationResult] = await ApplicationResult.filter(
        Q(user_id=user_id) & Q(notified=False)
    ).all()

    if not results:
        logger.info("[notifications] user_id=%s: no fresh results, skip", user_id)
        return

    # 3) максимум total_vacancies
    max_total = max(r.total_vacancies for r in results)

    # Кол-во отправленных откликов — суммарно по результатам
    sent_sum = sum(r.sent_applications for r in results)

    # 4) собрать уникальные skipped_tests
    all_skipped: List[str] = []
    for r in results:
        if r.skipped_tests:
            # ожидается JSON-массив строк/чисел
            all_skipped.extend([str(x) for x in r.skipped_tests])

    unique_skipped = _unique_preserve_order(all_skipped)

    # 5) составить сообщение
    text = _build_message(max_total_vacancies=max_total, sent_sum=sent_sum, skipped_ids=unique_skipped)

    # 6) отправить сообщение пользователю
    chat_id = int(user_id)
    try:
        logger.info("[notifications] sending to user_id=%s (results=%d, max_total=%d, sent_sum=%d, skipped=%d)",
                    user_id, len(results), max_total, sent_sum, len(unique_skipped))
        await _send_message(chat_id, text)

    except TelegramRetryAfter as e:
        logger.warning("[notifications] rate limit for user_id=%s, retry after %s sec", user_id, e.retry_after)
        await asyncio.sleep(e.retry_after)
        try:
            await _send_message(chat_id, text)
            logger.info("[notifications] sent on retry to user_id=%s", user_id)
        except Exception as e2:
            logger.exception("[notifications] second attempt failed for user_id=%s: %s", user_id, e2)
            return  # не помечаем notified, если не смогли отправить дважды

    except TelegramForbiddenError:
        logger.warning("[notifications] cannot send to user_id=%s: bot blocked or user didn't start the bot", user_id)
        # Можно помечать notified, чтобы не спамить впустую; решайте по бизнес-логике.
        # Здесь НЕ помечаем, чтобы попробовать в следующий раз, вдруг разблокируют.
        return

    except (TelegramBadRequest, TelegramNetworkError) as e:
        logger.exception("[notifications] telegram/network error for user_id=%s: %s", user_id, e)
        return

    except Exception as e:
        logger.exception("[notifications] unexpected error for user_id=%s: %s", user_id, e)
        return

    # Если дошли сюда — сообщение отправлено. Помечаем записи как notified.
    ids_to_update = [r.id for r in results]
    if ids_to_update:
        now = timezone.now()
        updated = await ApplicationResult.filter(id__in=ids_to_update).update(
            notified=True, notified_at=now
        )
        logger.info("[notifications] marked notified user_id=%s, updated=%d", user_id, updated)


async def notification_task(user_id: Optional[int | str] = None) -> None:
    """
    Отправляет уведомления:
      - если user_id передан — только этому пользователю,
      - если нет — всем пользователям с включёнными уведомлениями и активным статусом.
    """
    if user_id is not None:
        await _process_user(int(user_id))
        return

    # 1) получить список пользователей с включёнными уведомлениями
    # и активным статусом (user_status='active')
    user_ids: List[int] = await User.filter(
        Q(notifications=True) & Q(user_status="active")
    ).values_list("id", flat=True)

    if not user_ids:
        logger.info("[notifications] no users with notifications enabled")
        return

    # Обрабатываем пользователей последовательно (проще контролировать rate-limit Telegram)
    # При желании можно батчить/ограничивать параллелизм.
    for uid in user_ids:
        await _process_user(int(uid))