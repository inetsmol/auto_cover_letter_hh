from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.types import Message

router = Router()


@router.message()
async def fallback_message_handler(message: Message):
    await message.answer(
        "Не понимаю эту команду или сообщение.\n"
        "Пожалуйста, воспользуйтесь меню или напишите /start."
    )


@router.callback_query()
async def fallback_callback_handler(call: CallbackQuery):
    await call.answer("Некорректная или устаревшая кнопка.")

