# src/bot/keyboards/common.py
# aiogram v3.x
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Константа для текста кнопки — используйте её и в хендлерах (F.text == BTN_CANCEL)
BTN_CANCEL = "❌ Отмена"


def cancel_menu() -> ReplyKeyboardMarkup:
    """
    Клавиатура с одной кнопкой «Отмена» для выхода из текущего шага.
    Используется при ожидании ввода (например, ссылки на резюме).
    После нажатия кнопку можно скрыть, отправив новое сообщение с ReplyKeyboardRemove.
    """
    keyboard = [
        [KeyboardButton(text=BTN_CANCEL)],  # один ряд с одной кнопкой
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,     # компактная высота
        one_time_keyboard=True,   # Telegram попытается скрыть клавиатуру после нажатия
        selective=False,          # показывать всем
        # input_field_placeholder="Отправьте ссылку или нажмите «Отмена»"
    )
