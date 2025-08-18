# src/bot/handlers/notifications/settings.py
from aiogram import Router, F
from aiogram.types import Message

from src.config import config
from src.models import User
from src.bot.keyboards.main_menu import (
    BTN_NOTIF_ON,
    BTN_NOTIF_OFF,
    get_main_menu,
)

router = Router()

@router.message(F.text.in_({BTN_NOTIF_ON, BTN_NOTIF_OFF}))
async def toggle_notifications(message: Message):
    tg_id = message.from_user.id

    # Получаем пользователя (предполагается, что он уже создан при /start)
    user = await User.get_or_none(id=tg_id)

    # Переключаем флаг
    user.notifications = not user.notifications
    await user.save()

    print(f"user.notifications: {user.notifications}")

    status_text = "включены" if user.notifications else "выключены"

    is_admin = user.id in config.bot.admin_ids

    await message.answer(
        f"Уведомления {status_text}.",
        reply_markup=get_main_menu(is_admin=is_admin, notifications_enabled=user.notifications),
    )
