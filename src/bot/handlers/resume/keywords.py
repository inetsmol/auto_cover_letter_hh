# src/bot/handlers/resume/keywords.py
import re

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.bot.keyboards.common import cancel_menu
from src.bot.keyboards.resume_management import BTN_EDIT_KEYWORDS, BTN_EDIT_NEGATIVE, manage_resume_menu_plain
from src.bot.utils.telegram import remove_reply_markup_by_state
from src.models import Resume
from src.utils.formatters import format_resume_card

router = Router()

class AddResumeStates:
    waiting_for_positive_keywords = "resume:waiting_pos"
    waiting_for_negative_keywords = "resume:waiting_neg"

async def _require_resume_id(message: Message, state: FSMContext) -> str | None:
    data = await state.get_data()
    rid = data.get("resume_id")
    if not rid:
        await message.answer("Сначала выберите резюме в списке.")
        return None
    return rid

@router.message(F.text == BTN_EDIT_KEYWORDS)
async def start_positive(message: Message, state: FSMContext):
    rid = await _require_resume_id(message, state)
    if not rid:
        return
    sent = await message.answer(
        "Отправьте ключевые слова через пробелы или запятые.\nНапр.: <code>Python, Django, FastAPI</code>",
        reply_markup=cancel_menu(),
    )
    await state.update_data(msg_id=sent.message_id)
    await state.set_state(AddResumeStates.waiting_for_positive_keywords)

@router.message(AddResumeStates.waiting_for_positive_keywords)
async def save_positive(message: Message, state: FSMContext):
    await remove_reply_markup_by_state(message, state, msg_id_key="msg_id")
    words = [w.strip() for w in re.split(r"[,\s]+", (message.text or "")) if w.strip()]
    if not words:
        await message.answer("Пусто. Отправьте слова через пробелы или запятые.")
        return

    data = await state.get_data()
    rid = data.get("resume_id")
    resume = await Resume.get_or_none(id=rid)
    if not resume:
        await message.answer("Резюме не найдено.")
        await state.clear()
        return

    resume.positive_keywords = words
    await resume.save()
    await message.answer(f"Ключевые слова обновлены:\n<code>{', '.join(words)}</code>")
    await message.answer(format_resume_card(resume), reply_markup=manage_resume_menu_plain())
    await state.clear()

@router.message(F.text == BTN_EDIT_NEGATIVE)
async def start_negative(message: Message, state: FSMContext):
    rid = await _require_resume_id(message, state)
    if not rid:
        return
    sent = await message.answer(
        "Отправьте слова-исключения через пробелы или запятые.\nНапр.: <code>1C, PHP, фронтенд</code>",
        reply_markup=cancel_menu(),
    )
    await state.update_data(msg_id=sent.message_id)
    await state.set_state(AddResumeStates.waiting_for_negative_keywords)

@router.message(AddResumeStates.waiting_for_negative_keywords)
async def save_negative(message: Message, state: FSMContext):
    await remove_reply_markup_by_state(message, state, msg_id_key="msg_id")
    words = [w.strip() for w in re.split(r"[,\s]+", (message.text or "")) if w.strip()]
    if not words:
        await message.answer("Пусто. Отправьте слова через пробелы или запятые.")
        return

    data = await state.get_data()
    rid = data.get("resume_id")
    resume = await Resume.get_or_none(id=rid)
    if not resume:
        await message.answer("Резюме не найдено.")
        await state.clear()
        return

    resume.negative_keywords = words
    await resume.save()
    await message.answer(f"Слова-исключения обновлены:\n<code>{', '.join(words)}</code>")
    await message.answer(format_resume_card(resume), reply_markup=manage_resume_menu_plain())
    await state.clear()
