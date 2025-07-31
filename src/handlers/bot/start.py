# src/handlers/bot/start.py
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart

from src.models import User

router = Router()

@router.message(CommandStart())
async def start_handler(message: Message):
    tg_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    user = await User.get_or_none(id=tg_id)
    if not user:
        user = await User.create(
            id=tg_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
    await message.answer("👋 Привет! Я зарегистрировал тебя и готов к работе.")
