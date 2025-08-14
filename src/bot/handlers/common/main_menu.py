# src/bot/handlers/common/main_menu.py
# aiogram v3.x
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.bot.keyboards.main_menu import get_main_menu               # ← возвращает ReplyKeyboardMarkup
from src.bot.keyboards.resume_management import BTN_BACK_TO_MAIN     # "⬅️ В главное меню"
from src.bot.keyboards.common import BTN_CANCEL                      # "❌ Отмена"
from src.config import config

router = Router()


@router.message(F.text == BTN_BACK_TO_MAIN)
async def show_main_menu(message: Message, state: FSMContext) -> None:
    """
    Переход в главное меню по обычной кнопке «⬅️ В главное меню».
    ⚙️ Теперь это Message-хендлер (а не CallbackQuery).
    """
    # 1) Сброс состояния любых незавершённых сценариев
    await state.clear()

    # 2) Проверка роли для выбора нужного меню
    is_admin = message.from_user.id in config.bot.admin_ids

    # 3) Отправляем главное меню (ReplyKeyboard)
    await message.answer(
        "Главное меню:",
        reply_markup=get_main_menu(is_admin)
    )


@router.message(F.text == BTN_CANCEL)
async def cancel_and_main_menu(message: Message, state: FSMContext) -> None:
    """
    Обработка кнопки «❌ Отмена».
    Очищаем FSM и показываем главное меню.
    """
    # 1) Сброс состояния
    await state.clear()

    # 2) Ответ об отмене
    await message.answer("Действие отменено.")

    # 3) Возврат в главное меню (ReplyKeyboard)
    is_admin = message.from_user.id in config.bot.admin_ids
    await message.answer(
        "Главное меню:",
        reply_markup=get_main_menu(is_admin)
    )
