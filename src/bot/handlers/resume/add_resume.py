# src/bot/handlers/resume/add_resume.py
import re

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from src.bot.keyboards.main_menu import get_main_menu
from src.bot.keyboards.resume_management import manage_resume_menu
from src.bot.states.resume_states import AddResumeStates
from src.config import config

from src.models import Resume, User
from src.services.hh_client import hh_client
from src.services.resume.parser import extract_keywords

router = Router()

@router.callback_query(F.data == "resume:add")
async def add_resume_start(call: CallbackQuery, state: FSMContext):
    await call.message.delete()

    is_admin = call.from_user.id in config.bot.admin_ids
    await call.message.answer(
        "Пожалуйста, пришлите ссылку на своё резюме hh.ru в формате:\n\n"
        "https://hh.ru/resume/ВАШ_ID",
        reply_markup=get_main_menu(is_admin)
    )
    await state.set_state(AddResumeStates.waiting_for_resume_url)
    await call.answer()


@router.message(AddResumeStates.waiting_for_resume_url)
async def resume_url_received(message: Message, state: FSMContext):
    is_admin = message.from_user.id in config.bot.admin_ids
    resume_url = message.text.strip()
    match = re.match(r"^https://hh\.ru/resume/([a-fA-F0-9]{38})$", resume_url)
    if not match:
        await message.answer(
            "❗️Пожалуйста, отправьте корректную ссылку на резюме с hh.ru в формате:\n\n"
            "https://hh.ru/resume/ВАШ_ID",
            reply_markup=get_main_menu(is_admin)
        )
        return

    resume_id = match.group(1)
    try:
        resume_json = await hh_client.get_resume(resume_id)
    except Exception as e:
        await message.answer(
            f"❗️Ошибка при получении резюме: {e}\n\n"
            "Проверьте, что резюме доступно и ссылка корректна.",
            reply_markup=get_main_menu(is_admin)
        )
        return

    positive_keywords = extract_keywords(resume_json.get("title", ""))

    user = await User.get_or_none(id=message.from_user.id)
    resume, created = await Resume.get_or_create(
        id=resume_id,
        defaults={
            "user": user,
            "resume_json": resume_json,
            "positive_keywords": positive_keywords
        }
    )
    if not created:
        resume.user = user
        resume.resume_json = resume_json
        resume.positive_keywords = positive_keywords
        await resume.save()

    await message.answer(
        f"✅ Ссылка принята! ID резюме: <code>{resume_id}</code>\n\n"
        f"Ключевые слова: {', '.join(positive_keywords) if positive_keywords else 'не извлечены'}",
        reply_markup=manage_resume_menu(resume_id)
    )
    await state.clear()
