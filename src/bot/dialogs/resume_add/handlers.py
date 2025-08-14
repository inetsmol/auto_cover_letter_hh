# src/bot/dialogs/resume_add/handlers.py
from __future__ import annotations

import re

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button

from src.bot.dialogs.resume_add.states import AddResumeSG
from src.bot.keyboards.main_menu import get_main_menu
from src.config import config
from src.models import Resume, User
from src.services.hh_client import hh_client
from src.services.resume.parser import extract_keywords
from src.utils.formatters import format_resume_card

# Регулярка для ссылки на резюме HH (38 hex-символов)
_RESUME_URL_RE = re.compile(r"^https://hh\.ru/resume/([a-fA-F0-9]{38})$")

# ─────────────────────────────────────────────────────────────────────────────
# Навигация из других диалогов/окон
# ─────────────────────────────────────────────────────────────────────────────
async def open_add_dialog(_cq: CallbackQuery, _btn: Button, manager: DialogManager):
    """
    Открыть диалог добавления резюме.
    Вызывается, например, из списка резюме (кнопка «➕ Добавить резюме»).
    """
    await manager.start(AddResumeSG.ask_url, mode=StartMode.NORMAL)  # вложить в стек


# ─────────────────────────────────────────────────────────────────────────────
# Обработчики ввода и кнопок текущего диалога
# ─────────────────────────────────────────────────────────────────────────────
async def on_url_input(msg: Message, _inp: MessageInput, manager: DialogManager):
    """
    Принять ссылку, провалидировать, загрузить резюме из HH, сохранить в БД и
    перейти к окну результата.
    """
    url = (msg.text or "").strip()
    m = _RESUME_URL_RE.match(url)
    if not m:
        await msg.answer(
            "❗️Пожалуйста, отправьте корректную ссылку на резюме в формате:\n"
            "<code>https://hh.ru/resume/ВАШ_ID</code>"
        )
        return

    resume_id = m.group(1)

    # 1) Тянем резюме из HH API
    try:
        resume_json = await hh_client.get_resume(resume_id)
    except Exception as e:
        await msg.answer(
            f"❗️Ошибка при получении резюме: {e}\n"
            "Проверьте доступность резюме и корректность ссылки."
        )
        return

    # 2) Извлекаем ключевые слова из заголовка
    positive_keywords = extract_keywords(resume_json.get("title", ""))

    # 3) Сохраняем/обновляем в БД (привязываем к пользователю)
    user = await User.get_or_none(id=msg.from_user.id)
    resume, created = await Resume.get_or_create(
        id=resume_id,
        defaults={
            "user": user,
            "resume_json": resume_json,
            "positive_keywords": positive_keywords,
        },
    )
    if not created:
        resume.user = user
        resume.resume_json = resume_json
        resume.positive_keywords = positive_keywords
        await resume.save()

    # 4) Готовим данные для окна результата
    manager.dialog_data.update({
        "resume_id": resume_id,
        "card": format_resume_card(resume),
        "keywords": ", ".join(positive_keywords) if positive_keywords else "не извлечены",
    })

    await msg.answer(
        f"✅ Ссылка принята! ID резюме: <code>{resume_id}</code>\n"
        f"Ключевые слова: {manager.dialog_data['keywords']}"
    )

    # 5) Переходим к окну управление резюме
    from src.bot.dialogs.resumes.states import ResumesSG  # ленивый импорт допустим и тут
    await manager.start(
        ResumesSG.manage,
        data={"resume_id": resume_id},  # передаём rid в start_data
        mode=StartMode.RESET_STACK,  # закрываем текущий диалог, открываем Resumes
    )


async def to_manage_resume(cq: CallbackQuery, _btn: Button, manager: DialogManager):
    """
    Перейти к управлению только что добавленным резюме.
    Закрываем текущий диалог и открываем диалог «Резюме» в окне управления.
    """
    # ✅ ЛЕНИВЫЙ импорт
    from src.bot.dialogs.resumes.states import ResumesSG

    rid = manager.dialog_data.get("resume_id")
    # Сбрасываем текущий диалог и запускаем ResumesSG.manage с dialog_data
    await manager.start(
        ResumesSG.manage,
        data={"resume_id": rid},
        mode=StartMode.RESET_STACK,
    )


async def to_resumes_list(cq: CallbackQuery, _btn: Button, manager: DialogManager):
    """
    Вернуться к списку резюме: закрыть текущий диалог и открыть список.
    """
    # ✅ ЛЕНИВЫЙ импорт
    from src.bot.dialogs.resumes.states import ResumesSG
    await manager.start(ResumesSG.list, mode=StartMode.RESET_STACK)


async def to_main_menu(cq: CallbackQuery, _btn: Button, manager: DialogManager):
    """
    Завершить диалог и вернуть главное меню (ReplyKeyboard).
    """
    await cq.answer()
    await manager.done()
    is_admin = cq.from_user.id in config.bot.admin_ids
    await cq.message.answer("Главное меню:", reply_markup=get_main_menu(is_admin))
