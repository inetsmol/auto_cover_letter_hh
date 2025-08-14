# src/bot/dialogs/resumes/getters.py
from __future__ import annotations

from typing import Any, Dict, List
from aiogram_dialog import DialogManager

from src.models import Resume
from src.utils.formatters import format_resume_card

async def list_getter(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    """
    Данные для окна списка резюме.
    Возвращаем items: List[tuple[title, id]] для Select (title, resume_id).
    """
    user_id = dialog_manager.event.from_user.id
    resumes = await Resume.filter(user_id=user_id).all()
    items: List[tuple[str, str]] = [
        ((r.resume_json or {}).get("title", "Без названия"), r.id) for r in resumes
    ]
    return {"resumes": items, "count": len(items)}

async def manage_getter(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    """
    Достаём resume_id сначала из dialog_data, а если нет — из start_data,
    и кладём в dialog_data для последующих окон/обработчиков.
    """
    rid = dialog_manager.dialog_data.get("resume_id")

    if not rid:
        sd = dialog_manager.start_data or {}  # данные, переданные в manager.start(..., data=...)
        rid = sd.get("resume_id")
        if rid:
            dialog_manager.dialog_data["resume_id"] = rid  # запомним навсегда в рамках диалога

    resume = await Resume.get_or_none(id=rid)
    card = format_resume_card(resume) if resume else "Резюме не найдено."
    return {"card": card}
