# src/bot/handlers/resume/add_resume.py
from __future__ import annotations

import re

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.bot.keyboards.common import cancel_menu  # ← ДОЛЖНА вернуть ReplyKeyboardMarkup с кнопкой "Отмена"
from src.bot.keyboards.main_menu import get_main_menu  # ← должен возвращать ReplyKeyboardMarkup
from src.bot.keyboards.resume_management import (
    # список констант кнопок (используем текст для фильтра)
    BTN_ADD_RESUME, manage_resume_menu_plain,
)
from src.bot.states.resume_states import AddResumeStates
from src.bot.utils.telegram import remove_reply_markup_by_state  # удаляет предыдущую разметку по msg_id из state
from src.config import config
from src.models import Resume, User
from src.services.hh_client import hh_client
from src.services.resume.parser import extract_keywords
from src.utils.formatters import format_resume_card

router = Router()

# Регулярка для ссылки на резюме HH (hex из 38 символов)
RESUME_URL_RE = re.compile(r"^https://hh\.ru/resume/([a-fA-F0-9]{38})$")


@router.message(F.text == BTN_ADD_RESUME)
async def add_resume_start(message: Message, state: FSMContext) -> None:
    """
    Старт добавления резюме.
    Триггерится обычной кнопкой "➕ Добавить резюме" (ReplyKeyboard).
    Просим прислать ссылку и показываем клавиатуру с отменой.
    """
    sent = await message.answer(
        "Пожалуйста, пришлите ссылку на своё резюме hh.ru в формате:\n\n"
        "https://hh.ru/resume/ВАШ_ID",
        reply_markup=cancel_menu()  # ← ReplyKeyboard с кнопкой "Отмена"
    )
    # Сохраняем id этого сообщения, чтобы потом убрать у него клавиатуру (если нужно)
    await state.update_data(msg_id=sent.message_id)
    await state.set_state(AddResumeStates.waiting_for_resume_url)


@router.message(AddResumeStates.waiting_for_resume_url)
async def resume_url_received(message: Message, state: FSMContext) -> None:
    """
    Обрабатывает присланную ссылку на резюме.
    1) Валидируем формат
    2) Получаем JSON резюме из HH
    3) Сохраняем/обновляем запись в БД
    4) Показываем карточку резюме и меню управления им (ReplyKeyboard)
    """
    # Убираем клавиатуру у предыдущего "подсказочного" сообщения (если использовали one-off клавиатуру)
    await remove_reply_markup_by_state(message, state, msg_id_key="msg_id")

    resume_url = (message.text or "").strip()
    m = RESUME_URL_RE.match(resume_url)
    if not m:
        # Сообщение о некорректной ссылке + даём повторить ввод/отменить
        sent = await message.answer(
            "❗️Пожалуйста, отправьте корректную ссылку на резюме с hh.ru в формате:\n\n"
            "https://hh.ru/resume/ВАШ_ID",
            reply_markup=cancel_menu()
        )
        await state.update_data(msg_id=sent.message_id)
        return

    resume_id = m.group(1)

    # Получаем данные резюме из HH API
    try:
        resume_json = await hh_client.get_resume(resume_id)
    except Exception as e:
        # Сообщаем об ошибке и возвращаем главное меню
        await message.answer(
            f"❗️Ошибка при получении резюме: {e}\n\n"
            "Проверьте, что резюме доступно и ссылка корректна."
        )
        is_admin = message.from_user.id in config.bot.admin_ids
        await message.answer("Главное меню:", reply_markup=get_main_menu(is_admin))
        await state.clear()
        return

    # Извлекаем ключевые слова из заголовка
    positive_keywords = extract_keywords(resume_json.get("title", ""))

    # Привязываем резюме к пользователю и сохраняем
    user = await User.get_or_none(id=message.from_user.id)
    resume, created = await Resume.get_or_create(
        id=resume_id,
        defaults={
            "user": user,
            "resume_json": resume_json,
            "positive_keywords": positive_keywords,
        },
    )
    if not created:
        # Обновляем существующее резюме
        resume.user = user
        resume.resume_json = resume_json
        resume.positive_keywords = positive_keywords
        await resume.save()

    # Сообщаем об успехе
    await message.answer(
        f"✅ Ссылка принята! ID резюме: <code>{resume_id}</code>\n\n"
        f"Ключевые слова: {', '.join(positive_keywords) if positive_keywords else 'не извлечены'}"
    )

    # Показываем карточку резюме и меню управления конкретным резюме (ReplyKeyboard с RID)
    await message.answer(
        format_resume_card(resume),
        reply_markup=manage_resume_menu_plain()
    )

    await state.clear()
