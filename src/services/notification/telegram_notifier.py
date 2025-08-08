# src/services/notification/telegram_notifier.py

from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest

from src.bot_init import bot  # aiogram Bot


async def send_processing_summary(
    *,
    user_id: int,
    run_type: str,
    resumes_enqueued: int,
) -> None:
    """
    Короткое уведомление пользователю о том, что задачи поставлены.
    """
    rt_human = {
        "free_daily": "Ежедневный запуск (FREE)",
        "paid_hourly": "Почасовой запуск (PLUS/PRO)",
        "bulk": "Массовый запуск",
        "manual": "Ручной запуск",
    }.get(run_type, "Запуск")

    text = (
        f"✅ {rt_human}\n"
        f"🔧 Постановка задач завершена.\n"
        f"📄 Резюме в обработке: {resumes_enqueued}"
    )

    try:
        await bot.send_message(chat_id=user_id, text=text)
    except TelegramBadRequest:
        # молча глотаем, чтобы не валить воркер
        pass
