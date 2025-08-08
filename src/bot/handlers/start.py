# src/bot/handlers/start.py
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from src.config import config
from src.bot.keyboards.main_menu import get_main_menu
from src.models import User
from src.services.subscription.service import ensure_subscription_for_user

router = Router()

@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    u = message.from_user

    # 1) создаём/находим пользователя
    user, created = await User.get_or_create(
        id=u.id,
        defaults={
            "username": u.username or "",
            "first_name": u.first_name or "",
            "last_name": u.last_name or "",
        },
    )

    # 2) бережно обновляем только изменившиеся поля (меньше лишних UPDATE)
    if not created:
        to_update = []
        new_username = u.username or ""
        new_first = u.first_name or ""
        new_last = u.last_name or ""

        if user.username != new_username:
            user.username = new_username
            to_update.append("username")
        if user.first_name != new_first:
            user.first_name = new_first
            to_update.append("first_name")
        if user.last_name != new_last:
            user.last_name = new_last
            to_update.append("last_name")

        if to_update:
            await user.save(update_fields=to_update)

    # 3) гарантируем наличие подписки
    await ensure_subscription_for_user(user)

    # 4) UI
    is_admin = u.id in config.bot.admin_ids
    keyboard = get_main_menu(is_admin)

    await state.clear()
    await message.answer(
        text="👋 Привет! Я зарегистрировал тебя и готов к работе.",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "menu:main")
async def show_main_menu(call: CallbackQuery, state):
    await call.message.delete()
    await state.clear()
    is_admin = call.from_user.id in config.bot.admin_ids
    await call.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu(is_admin)
    )
    await call.answer()


@router.callback_query(F.data == "menu:cancel")
async def cancel_and_main_menu(call: CallbackQuery, state):
    await call.message.delete()
    await state.clear()
    is_admin = call.from_user.id in config.bot.admin_ids
    await call.message.answer("Действие отменено.")
    await call.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu(is_admin)
    )
    await call.answer()