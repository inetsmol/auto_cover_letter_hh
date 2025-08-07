# src/bot/keyboards/main_menu.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def user_main_menu():
    """Главное меню для обычного пользователя."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📄 Мои резюме", callback_data="menu:resumes"),
            InlineKeyboardButton(text="🚀 Управление задачами", callback_data="menu:tasks"),
        ],
        [
            InlineKeyboardButton(text="🔔 Уведомления", callback_data="menu:notifications"),
            InlineKeyboardButton(text="💳 Подписка", callback_data="menu:subscription"),
        ],
    ])

def admin_main_menu():
    """Главное меню для администратора (добавляет админ-панель)."""
    kb = user_main_menu().inline_keyboard
    kb.append([
        InlineKeyboardButton(text="🛠️ Админ-панель", callback_data="menu:admin"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# Если нужно автоматически определять меню:
def get_main_menu(is_admin: bool = False):
    return admin_main_menu() if is_admin else user_main_menu()
