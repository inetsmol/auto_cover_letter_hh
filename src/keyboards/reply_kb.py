# src/keyboards/reply_kb.py
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_keyboard(is_admin: bool, is_persistent: bool = True):
    # Создаем кнопки с локализованным текстом
    add_resume_button = KeyboardButton(text="Добавить резюме")
    get_resume_button = KeyboardButton(text="Мои резюме")
    start_subscribe_management_button = KeyboardButton(text="Управление подпиской")
    start_admin_settings_button = KeyboardButton(text="Настройки администратора")

    # Создаем объект клавиатуры
    keyboard = [
        [add_resume_button, get_resume_button],
        [start_subscribe_management_button]
    ]

    if is_admin:
        keyboard.append([start_admin_settings_button])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=False, is_persistent=is_persistent)
