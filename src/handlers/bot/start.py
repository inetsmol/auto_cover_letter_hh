# src/handlers/bot/start.py
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.filters import CommandStart

from src.config import config
from src.keyboards.reply_kb import get_keyboard
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
        is_user_admin = True
    else:
        is_user_admin = False
    keyboard = get_keyboard(is_user_admin)
    await message.answer(text="👋 Привет! Я зарегистрировал тебя и готов к работе.", reply_markup=keyboard)
    await state.clear()

