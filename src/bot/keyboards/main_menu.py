# src/bot/keyboards/main_menu.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

BTN_RESUMES = "📄 Мои резюме"
BTN_TASKS = "🚀 Управление задачами"
BTN_NOTIF_ON = "🔔 Включить уведомления"
BTN_NOTIF_OFF = "🔕 Выключить уведомления"
BTN_SUBSCRIPTION = "💳 Подписка"
BTN_ADMIN = "🛠️ Админ-панель"


def notifications_button_title(enabled: bool) -> str:
    """Возвращает подпись кнопки в зависимости от статуса."""
    return BTN_NOTIF_ON if enabled else BTN_NOTIF_OFF


def user_main_menu(notifications_enabled: bool = False) -> ReplyKeyboardMarkup:
    """
    Главное меню для обычного пользователя.
    Возвращает ReplyKeyboard (обычные кнопки под полем ввода).
    """
    keyboard = [
        [KeyboardButton(text=BTN_RESUMES), KeyboardButton(text=BTN_TASKS)],
        [KeyboardButton(text=notifications_button_title(notifications_enabled)), KeyboardButton(text=BTN_SUBSCRIPTION)],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        selective=False,
    )


def admin_main_menu(notifications_enabled: bool = False) -> ReplyKeyboardMarkup:
    """
    Главное меню для администратора.
    Добавляет ряд с кнопкой админ-панели.
    """
    base = user_main_menu(notifications_enabled=notifications_enabled)
    keyboard = list(base.keyboard)  # копия, чтобы не мутировать исходный объект
    keyboard.append([KeyboardButton(text=BTN_ADMIN)])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        selective=False,
    )


def get_main_menu(is_admin: bool = False, notifications_enabled: bool = False) -> ReplyKeyboardMarkup:
    """Автовыбор меню по роли пользователя и статусу уведомлений."""
    return admin_main_menu(notifications_enabled) if is_admin else user_main_menu(notifications_enabled)


def remove_keyboard() -> ReplyKeyboardRemove:
    """Сервисная разметка для скрытия клавиатуры."""
    return ReplyKeyboardRemove()

