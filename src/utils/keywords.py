# src/utils/keywords.py
"""
Утилиты для работы с ключевыми словами резюме и вакансий.
"""

from typing import Iterable, Optional


def build_search_query(
    positive_keywords: Optional[Iterable[str]],
    negative_keywords: Optional[Iterable[str]] = None,
) -> str:
    """
    Формирует строку поиска для HH API:
    - positive соединяются через "OR"
    - negative добавляются через "NOT <word>"
    Пример:
        pos=["python", "fastapi"], neg=["php", "ruby"]
        -> "python OR fastapi NOT php NOT ruby"
    """
    if not positive_keywords:
        return ""

    # Чистим и отбрасываем пустые слова
    pos_clean = [w.strip() for w in positive_keywords if w and w.strip()]
    neg_clean = [w.strip() for w in (negative_keywords or []) if w and w.strip()]

    search = " OR ".join(pos_clean)
    if neg_clean:
        search += " " + " ".join(f"NOT {w}" for w in neg_clean)

    return search
