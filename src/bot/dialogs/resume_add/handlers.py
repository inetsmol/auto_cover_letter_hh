# src/bot/dialogs/resume_add/handlers.py
from __future__ import annotations

import re

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.filters.command import CommandObject
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button

from src.bot.dialogs.common import close_all_dialogs_and_show_main_menu
from src.bot.dialogs.resume_add.states import AddResumeSG
from src.bot.tasks.resume import add_resume_task
from src.services.hh.auth.token_manager import tm
from src.utils.formatters import format_resume_card

# Роутер этого модуля
router = Router()

# Регулярка для ссылки на резюме HH (38 hex-символов)
_RESUME_URL_RE = re.compile(r"^https://hh\.ru/resume/([a-fA-F0-9]{38})$")


# ─────────────────────────────────────────────────────────────────────────────
# Навигация из других диалогов/окон
# ─────────────────────────────────────────────────────────────────────────────
async def open_add_dialog(_cq: CallbackQuery, _btn: Button, dialog_manager: DialogManager):
    """
    Открыть диалог добавления резюме.
    Если у пользователя нет валидного access_token HH — показываем окно авторизации.
    """
    tg_id = _cq.from_user.id
    try:
        # Гарантируем валидный access_token (при необходимости обновит по refresh)
        _ = await tm.ensure_access(subject=tg_id)
    except Exception:
        # Нет токена — стартуем окно авторизации с предсобранной ссылкой
        auth_url = tm.authorization_url(state=str(tg_id))
        await dialog_manager.start(AddResumeSG.auth, data={"auth_url": auth_url}, mode=StartMode.NORMAL)
        await _cq.answer()
        return

    # Токен есть — сразу к вводу ссылки
    await dialog_manager.start(AddResumeSG.ask_url, mode=StartMode.NORMAL)


async def check_auth_and_go(cq: CallbackQuery, _btn: Button, dialog_manager: DialogManager):
    """
    Кнопка «🔄 Я авторизовался»: проверяем наличие валидного токена и
    переходим к вводу ссылки.
    """
    try:
        _ = await tm.ensure_access(subject=cq.from_user.id)
    except Exception:
        await cq.answer("Авторизация ещё не завершена", show_alert=True)
        return

    await cq.answer()
    await dialog_manager.switch_to(AddResumeSG.ask_url)


# Deep-link: /start <payload>. Нужен payload == "add_resume"
@router.message(CommandStart(deep_link=True))
async def start_add_resume_deeplink(
    message: Message,
    command: CommandObject,
    dialog_manager: DialogManager,  # ВАЖНО: именно dialog_manager
):
    """
    Обрабатываем /start <payload>.
    Открываем окно ввода ссылки, если payload == 'add_resume'.
    """
    payload = (command.args or "").strip()
    if payload == "add_resume":
        await dialog_manager.start(AddResumeSG.ask_url, mode=StartMode.RESET_STACK)


# ─────────────────────────────────────────────────────────────────────────────
# Обработчики ввода и кнопок текущего диалога
# ─────────────────────────────────────────────────────────────────────────────
async def on_url_input(msg: Message, _inp: MessageInput, dialog_manager: DialogManager):
    """
    Принять ссылку, провалидировать, загрузить резюме из HH, сохранить в БД и
    перейти в управление резюме.
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

    # На всякий случай — проверим токен ещё раз (мог истечь)
    try:
        _ = await tm.ensure_access(subject=msg.from_user.id)
    except Exception:
        auth_url = tm.authorization_url(state=str(msg.from_user.id))
        await msg.answer(
            "Сессия hh.ru недействительна. Авторизуйтесь и попробуйте ещё раз:\n" + auth_url
        )
        return
    try:
        resume, positive_keywords = await add_resume_task(msg.from_user.id, resume_id)
        # Кладём полезные данные (если где-то понадобятся)
        dialog_manager.dialog_data.update({
            "resume_id": resume_id,
            "card": format_resume_card(resume),
            "keywords": ", ".join(positive_keywords) if positive_keywords else "не извлечены",
        })

        # Сразу переходим в управление выбранным резюме
        from src.bot.dialogs.resumes.states import ResumesSG  # ленивый импорт
        await dialog_manager.start(
            ResumesSG.manage,
            data={"resume_id": resume_id},
            mode=StartMode.RESET_STACK,
        )
    except Exception as e:
        await msg.answer(
            f"Неожиданная ошибка: {e}"
        )


async def to_manage_resume(cq: CallbackQuery, _btn: Button, dialog_manager: DialogManager):
    """
    Перейти к управлению текущим резюме.
    """
    from src.bot.dialogs.resumes.states import ResumesSG  # ленивый импорт
    rid = dialog_manager.dialog_data.get("resume_id")
    await dialog_manager.start(
        ResumesSG.manage,
        data={"resume_id": rid},
        mode=StartMode.RESET_STACK,
    )


async def to_resumes_list(cq: CallbackQuery, _btn: Button, dialog_manager: DialogManager):
    """
    Вернуться к списку резюме.
    """
    from src.bot.dialogs.resumes.states import ResumesSG  # ленивый импорт
    await dialog_manager.start(ResumesSG.list, mode=StartMode.RESET_STACK)


async def to_main_menu(cq: CallbackQuery, _btn: Button, dialog_manager: DialogManager):
    """Любой возврат в главное меню из диалога добавления резюме."""
    await close_all_dialogs_and_show_main_menu(cq, dialog_manager)
