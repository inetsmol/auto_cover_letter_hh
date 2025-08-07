# src/bot/handlers/resume/keywords.py
import re

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.keyboards.main_menu import cancel_menu
from src.bot.keyboards.resume_management import manage_resume_menu
from src.bot.states.resume_states import AddResumeStates
from src.bot.utils.telegram import remove_reply_markup_by_state
from src.models import Resume
from src.utils.formatters import format_resume_card

router = Router()

@router.callback_query(F.data.regexp(r"^resume:keywords:(.+)"))
async def handle_add_positive_keywords_callback(call: CallbackQuery, state: FSMContext):
    await call.message.delete()

    resume_id = call.data.split(":")[-1]
    await state.update_data(resume_id=resume_id)
    sent = await call.message.answer(
        "Пожалуйста, отправьте список ключевых слов (навыков), "
        "разделяя их пробелами или запятыми.\n\n"
        "Пример: <code>Python Django FastAPI</code>\n"
        "или\n"
        "<code>Python, Django, FastAPI</code>",
        reply_markup=cancel_menu()
    )
    await state.update_data(msg_id=sent.message_id)
    await state.set_state(AddResumeStates.waiting_for_positive_keywords)
    await call.answer()


@router.message(AddResumeStates.waiting_for_positive_keywords)
async def receive_positive_keywords(message: Message, state: FSMContext):
    await remove_reply_markup_by_state(message, state, msg_id_key="msg_id")
    text = message.text.strip()
    keywords = [w.strip() for w in re.split(r"[,\s]+", text) if w.strip()]
    if not keywords:
        await message.answer("Список не распознан. Пожалуйста, отправьте навыки через пробелы или запятые.")
        return

    data = await state.get_data()
    resume_id = data.get("resume_id")
    resume = await Resume.get_or_none(id=resume_id)
    if not resume:
        await message.answer("Ошибка: резюме не найдено.")
        await state.clear()
        return

    resume.positive_keywords = keywords
    await resume.save()
    await message.answer(f"Ключевые слова успешно добавлены:\n<code>{', '.join(keywords)}</code>")
    await message.answer(
        format_resume_card(resume),
        reply_markup=manage_resume_menu(resume_id)
    )
    await state.clear()


@router.callback_query(F.data.regexp(r"^resume:negative:(.+)"))
async def handle_add_negative_keywords_callback(call: CallbackQuery, state: FSMContext):
    await call.message.delete()

    resume_id = call.data.split(":")[-1]
    await state.update_data(resume_id=resume_id)
    sent = await call.message.answer(
        "Отправьте список слов, которые должны быть исключены при поиске вакансий (разделяйте их пробелами или запятыми).\n\n"
        "Пример: <code>1C PHP фронтенд</code>\n"
        "или\n"
        "<code>1C, PHP, фронтенд</code>",
        reply_markup=cancel_menu()
    )
    await state.update_data(msg_id=sent.message_id)
    await state.set_state(AddResumeStates.waiting_for_negative_keywords)
    await call.answer()


@router.message(AddResumeStates.waiting_for_negative_keywords)
async def receive_negative_keywords(message: Message, state: FSMContext):
    await remove_reply_markup_by_state(message, state, msg_id_key="msg_id")
    text = message.text.strip()
    keywords = [w.strip() for w in re.split(r"[,\s]+", text) if w.strip()]
    if not keywords:
        await message.answer("Список не распознан. Пожалуйста, отправьте слова через пробелы или запятые.")
        return

    data = await state.get_data()
    resume_id = data.get("resume_id")
    resume = await Resume.get_or_none(id=resume_id)
    if not resume:
        await message.answer("Ошибка: резюме не найдено.")
        await state.clear()
        return

    resume.negative_keywords = keywords
    await resume.save()
    await message.answer(f"Негативные слова успешно добавлены:\n<code>{', '.join(keywords)}</code>")
    await message.answer(
        format_resume_card(resume),
        reply_markup=manage_resume_menu(resume_id)
    )
    await state.clear()
