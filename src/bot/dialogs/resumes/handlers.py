# src/bot/dialogs/resumes/handlers.py
from __future__ import annotations

import re
from typing import Any, List

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.input import MessageInput

from src.bot.dialogs.resumes.states import ResumesSG
from src.bot.keyboards.main_menu import get_main_menu
from src.config import config
from src.models import Resume

# ==========================
# Навигация
# ==========================
async def on_resume_selected(cq: CallbackQuery, _w: Any, manager: DialogManager, item_id: str):
    """
    Выбор элемента из Select: сохраняем resume_id и переходим в окно управления.
    """
    manager.dialog_data["resume_id"] = item_id
    await manager.switch_to(ResumesSG.manage)

async def to_pos_input(_cq: CallbackQuery, _btn: Button, manager: DialogManager):
    """Переход к вводу позитивных ключевых слов."""
    await manager.switch_to(ResumesSG.pos_input)

async def to_neg_input(_cq: CallbackQuery, _btn: Button, manager: DialogManager):
    """Переход к вводу негативных слов."""
    await manager.switch_to(ResumesSG.neg_input)

async def toggle_status(cq: CallbackQuery, _btn: Button, manager: DialogManager):
    """
    Переключить статус активности резюме и перерисовать окно.
    """
    rid = manager.dialog_data.get("resume_id")
    resume = await Resume.get_or_none(id=rid)
    if not resume:
        await cq.message.answer("Резюме не найдено.")
        return
    resume.status = "inactive" if resume.status == "active" else "active"
    await resume.save()
    await manager.switch_to(ResumesSG.manage)

async def ask_delete(_cq: CallbackQuery, _btn: Button, manager: DialogManager):
    """Открыть окно подтверждения удаления."""
    await manager.switch_to(ResumesSG.confirm_delete)

async def do_delete(_cq: CallbackQuery, _btn: Button, manager: DialogManager):
    """Удалить резюме и вернуться к списку."""
    rid = manager.dialog_data.get("resume_id")
    if rid:
        await Resume.filter(id=rid).delete()
    await manager.switch_to(ResumesSG.list)

# Кнопка «⬅️ В главное меню»: закрыть диалог и вернуть ReplyKeyboard
async def to_main_menu(cq: CallbackQuery, _btn: Button, manager: DialogManager):
    await cq.answer()
    await manager.done()
    is_admin = cq.from_user.id in config.bot.admin_ids
    await cq.message.answer("Главное меню:", reply_markup=get_main_menu(is_admin))

# ==========================
# Ввод текстов (MessageInput)
# ==========================
_WORDS_RE = re.compile(r"[,\s]+")

def _parse_words(text: str) -> List[str]:
    """Разбор слов через пробелы/запятые."""
    return [w.strip() for w in _WORDS_RE.split(text or "") if w.strip()]

async def on_pos_words(msg: Message, _inp: MessageInput, manager: DialogManager):
    """Сохранение позитивных ключевых слов и возврат к управлению."""
    words = _parse_words(msg.text)
    if not words:
        await msg.answer("Пусто. Отправьте слова через пробелы или запятые.")
        return
    rid = manager.dialog_data.get("resume_id")
    resume = await Resume.get_or_none(id=rid)
    if not resume:
        await msg.answer("Резюме не найдено.")
        return
    resume.positive_keywords = words
    await resume.save()
    await msg.answer(f"Ключевые слова обновлены:\n<code>{', '.join(words)}</code>")
    await manager.switch_to(ResumesSG.manage)

async def on_neg_words(msg: Message, _inp: MessageInput, manager: DialogManager):
    """Сохранение негативных слов и возврат к управлению."""
    words = _parse_words(msg.text)
    if not words:
        await msg.answer("Пусто. Отправьте слова через пробелы или запятые.")
        return
    rid = manager.dialog_data.get("resume_id")
    resume = await Resume.get_or_none(id=rid)
    if not resume:
        await msg.answer("Резюме не найдено.")
        return
    resume.negative_keywords = words
    await resume.save()
    await msg.answer(f"Слова-исключения обновлены:\n<code>{', '.join(words)}</code>")
    await manager.switch_to(ResumesSG.manage)
