# src/bot/keyboards/resume_management.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

BTN_ADD_RESUME = "➕ Добавить резюме"
BTN_BACK_TO_MAIN = "⬅️ В главное меню"
BTN_BACK_TO_RESUMES = "⬅️ К списку резюме"
BTN_EDIT_KEYWORDS = "⚙️ Ключевые слова"
BTN_EDIT_NEGATIVE = "🚫 Слова-исключения"
BTN_TOGGLE_STATUS = "🔄 Изменить статус"
BTN_DELETE_RESUME = "🗑️ Удалить"

def resumes_list_menu_numbered(titles: list[str]) -> ReplyKeyboardMarkup:
    """Список резюме: '1) Title', '2) Title' ... — без встроенного ID."""
    rows = [[KeyboardButton(text=f"{i+1}) {t}")] for i, t in enumerate(titles)]
    rows.append([KeyboardButton(text=BTN_ADD_RESUME), KeyboardButton(text=BTN_BACK_TO_MAIN)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=False)

def manage_resume_menu_plain() -> ReplyKeyboardMarkup:
    """Меню управления выбранным резюме — без ID, используем FSM для хранения resume_id."""
    rows = [
        [KeyboardButton(text=BTN_EDIT_KEYWORDS), KeyboardButton(text=BTN_EDIT_NEGATIVE)],
        [KeyboardButton(text=BTN_TOGGLE_STATUS)],
        [KeyboardButton(text=BTN_DELETE_RESUME)],
        [KeyboardButton(text=BTN_BACK_TO_RESUMES), KeyboardButton(text=BTN_BACK_TO_MAIN)],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)
