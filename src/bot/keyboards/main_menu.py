# src/bot/keyboards/main_menu.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

BTN_RESUMES = "📄 Мои резюме"
BTN_TASKS = "🚀 Управление задачами"
BTN_NOTIFICATIONS = "🔔 Уведомления"
BTN_SUBSCRIPTION = "💳 Подписка"
BTN_ADMIN = "🛠️ Админ-панель"


def user_main_menu() -> ReplyKeyboardMarkup:
    """
    Главное меню для обычного пользователя.
    Возвращает ReplyKeyboard (обычные кнопки под полем ввода).
    """
    # Каждая вложенная коллекция — это ряд (row) кнопок.
    keyboard = [
        [KeyboardButton(text=BTN_RESUMES), KeyboardButton(text=BTN_TASKS)],
        [KeyboardButton(text=BTN_NOTIFICATIONS), KeyboardButton(text=BTN_SUBSCRIPTION)],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,     # подгоняет клавиатуру под экран
        one_time_keyboard=False,  # не скрывать автоматически после нажатия
        selective=False,          # показывать всем
        # input_field_placeholder="Выберите действие…"  # при желании можно добавить плейсхолдер
    )


def admin_main_menu() -> ReplyKeyboardMarkup:
    """
    Главное меню для администратора.
    Добавляет ряд с кнопкой админ-панели.
    """
    # Берём базовое меню и добавляем ряд с админ-кнопкой.
    base = user_main_menu()
    keyboard = list(base.keyboard)  # копия, чтобы не мутировать исходный объект
    keyboard.append([KeyboardButton(text=BTN_ADMIN)])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        selective=False,
    )


def get_main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Автовыбор меню по роли пользователя."""
    return admin_main_menu() if is_admin else user_main_menu()


def remove_keyboard() -> ReplyKeyboardRemove:
    """
    Сервисная разметка для скрытия клавиатуры.
    Используйте при выходе из меню или в свободном вводе.
    """
    return ReplyKeyboardRemove()

