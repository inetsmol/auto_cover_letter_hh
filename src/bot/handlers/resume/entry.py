# src/bot/handlers/resume/entry.py
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram_dialog import DialogManager, StartMode

from src.bot.keyboards.main_menu import BTN_RESUMES
from src.bot.dialogs.resumes import ResumesSG

router = Router()

@router.message(F.text == BTN_RESUMES)
async def open_resumes_dialog(message: Message, dialog_manager: DialogManager):
    # 🧹 Свернуть ReplyKeyboard перед стартом диалога
    # Telegram скрывает клавиатуру при получении сообщения с ReplyKeyboardRemove
    await message.answer("Открываю раздел «Резюме»…", reply_markup=ReplyKeyboardRemove())
    # Запускаем диалог
    await dialog_manager.start(ResumesSG.list, mode=StartMode.RESET_STACK)
