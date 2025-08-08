# src/services/ai/cover_letter_service.py
from __future__ import annotations

from typing import List, Dict

from src.services.ai.prompt_manager import generate_system_prompt, user_prompt
from src.services.ai.openai_client import chat_complete


async def generate_cover_letter(resume_text: str, vacancy_text: str) -> str:
    """
    Бизнес-логика генерации сопроводительного письма:
    - Формирует system/user промпты
    - Делегирует вызов LLM в openai_client.chat_complete
    - Возвращает финальный текст письма
    """
    system = generate_system_prompt(resume_text, vacancy_text)

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_prompt},
    ]

    # Можно подстраивать параметры под конкретные шаблоны
    text = await chat_complete(
        messages
    )

    return text.strip()
