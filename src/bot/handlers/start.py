# src/bot/handlers/start.py
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from src.config import config
from src.bot.keyboards.main_menu import get_main_menu
from src.models import User

router = Router()

@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    user, created = await User.get_or_create(
        id=tg_id,
        defaults={
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
        }
    )
    if not created:
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        await user.save()

    if message.from_user.id in config.bot.admin_ids:
        is_admin = True
    else:
        is_admin = False
    keyboard = get_main_menu(is_admin)
    await message.answer(text="👋 Привет! Я зарегистрировал тебя и готов к работе.", reply_markup=keyboard)
    await state.clear()


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