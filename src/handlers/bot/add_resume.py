# src/handlers/bot/add_resume.py
import re

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from src.config import config
from src.keyboards.reply_kb import get_keyboard
from src.keyboards.resume_kb import get_resume_actions_inline_kb
from src.models import Resume, User
from src.services.hh_client import hh_client
from src.services.resume import extract_keywords
from src.states.user_states import AddResumeStates

router = Router()


@router.message(lambda m: m.text == "Добавить резюме")
async def add_resume_start(message: Message, state: FSMContext):
    if message.from_user.id in config.bot.admin_ids:
        is_user_admin = True
    else:
        is_user_admin = False
    await message.answer("Пожалуйста, пришли ссылку на своё резюме hh.ru в формате:\n\n"
                         "https://hh.ru/resume/ВАШ_ID",
                         reply_markup=get_keyboard(is_user_admin)
                         )
    await state.set_state(AddResumeStates.waiting_for_resume_url)


@router.message(AddResumeStates.waiting_for_resume_url)
async def resume_url_received(message: Message, state: FSMContext):
    if message.from_user.id in config.bot.admin_ids:
        is_user_admin = True
    else:
        is_user_admin = False

    resume_url = message.text.strip()
    match = re.match(r"^https://hh\.ru/resume/([a-fA-F0-9]{38})$", resume_url)
    if not match:
        await message.answer("❗️Пожалуйста, отправь корректную ссылку на резюме с hh.ru в формате:\n\n"
                             "https://hh.ru/resume/ВАШ_ID",
                             reply_markup=get_keyboard(is_user_admin)
                             )
        # Сохраняем state, не сбрасываем!
        return

    resume_id = match.group(1)

    try:
        resume_json = await hh_client.get_resume(resume_id)
    except Exception as e:
        await message.answer(f"❗️Ошибка при получении резюме: {e}\n\n"
                             "Проверьте, что резюме доступно и ссылка корректна.",
                             reply_markup=get_keyboard(is_user_admin))
        return

    positive_keywords = extract_keywords(resume_json["title"])

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
        # Если резюме уже было — обновляем данные и пользователя на всякий случай
        resume.user = user
        resume.resume_json = resume_json
        resume.positive_keywords = positive_keywords
        await resume.save()
    # Здесь дальше твоя логика (сохраняем resume_id, привязываем к юзеру и т.д.)
    await message.answer(
        f"✅ Ссылка принята! ID резюме: <code>{resume_id}</code>\n\n"
        f"Ключевые слова: {', '.join(positive_keywords)}",
        reply_markup=get_resume_actions_inline_kb(resume_id)
    )
    await state.clear()


@router.callback_query(F.data.startswith("add_positive:"))
async def handle_add_positive_keywords_callback(call: CallbackQuery, state: FSMContext):
    resume_id = call.data.split(":", 1)[1]
    await state.update_data(resume_id=resume_id)  # Сохраним resume_id в контекст
    await call.message.answer(
        "Пожалуйста, отправьте список ключевых слов (навыков), "
        "разделяя их пробелами или запятыми.\n\n"
        "Пример: <code>Python Django FastAPI</code>\n"
        "или\n"
        "<code>Python, Django, FastAPI</code>"
    )
    await state.set_state(AddResumeStates.waiting_for_positive_keywords)
    await call.answer()  # Убираем "часики" с кнопки


@router.message(AddResumeStates.waiting_for_positive_keywords)
async def receive_positive_keywords(message: Message, state: FSMContext):
    text = message.text.strip()
    # Парсим слова: разделители — пробел или запятая, возможны смешанные
    keywords = [w.strip() for w in re.split(r"[,\s]+", text) if w.strip()]

    if not keywords:
        await message.answer("Список не распознан. Пожалуйста, отправьте навыки через пробелы или запятые.")
        return

    # Достаем resume_id из состояния
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
    await state.clear()


@router.callback_query(F.data.startswith("add_negative:"))
async def handle_add_negative_keywords_callback(call: CallbackQuery, state: FSMContext):
    resume_id = call.data.split(":", 1)[1]
    await state.update_data(resume_id=resume_id)
    await call.message.answer(
        "Отправьте список слов, которые должны быть исключены при поиске вакансий (разделяйте их пробелами или запятыми).\n\n"
        "Пример: <code>1C PHP фронтенд</code>\n"
        "или\n"
        "<code>1C, PHP, фронтенд</code>"
    )
    await state.set_state(AddResumeStates.waiting_for_negative_keywords)
    await call.answer()


@router.message(AddResumeStates.waiting_for_negative_keywords)
async def receive_negative_keywords(message: Message, state: FSMContext):
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
    await state.clear()


@router.callback_query(F.data.startswith("start_apply"))
async def handle_start_apply_callback(call: CallbackQuery, state: FSMContext):
    resume_id = call.data.split(":", 1)[1]

    resume = await Resume.get_or_none(id=resume_id)
    if not resume:
        await call.message.answer("Резюме не найдено.")
        await state.clear()
        await call.answer()
        return

    resume.status = "active"
    await resume.save()

    await call.message.answer(
        f"🚀 Запущена отправка откликов для резюме <code>{resume_id}</code>.\n"
    )
    await state.clear()
    await call.answer()  # Убираем "часики" с кнопки


@router.message(lambda m: m.text == "Мои резюме")
async def my_resumes_handler(message: Message, state: FSMContext):
    """Показывает список резюме пользователя"""
    user_id = message.from_user.id

    resumes = await Resume.filter(user_id=user_id).all()

    if not resumes:
        await message.answer("У вас пока нет добавленных резюме.\n\n"
                             "Используйте кнопку 'Добавить резюме' чтобы добавить первое резюме.")
        return

    response_parts = ["📄 **Ваши резюме:**\n"]

    for resume in resumes:
        status_emoji = "✅" if resume.status == "active" else "⏸"

        # Извлекаем название из resume_json
        title = "Не указано"
        if resume.resume_json and isinstance(resume.resume_json, dict):
            title = resume.resume_json.get('title', 'Не указано')

        response_parts.append(
            f"{status_emoji} **{title}**\n"
            f"ID: `{resume.id}`\n"
            f"Статус: {resume.status}\n"
            f"Ключевые слова: {', '.join(resume.positive_keywords or [])}\n"
        )

        if resume.negative_keywords:
            response_parts.append(f"Исключения: {', '.join(resume.negative_keywords)}\n")

        response_parts.append("─" * 30 + "\n")

    await message.answer("\n".join(response_parts))