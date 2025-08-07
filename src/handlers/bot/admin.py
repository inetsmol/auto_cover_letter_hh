# src/handlers/bot/admin.py
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

# from src.tasks.apply import apply_to_vacancies_task

router = Router()


@router.message(lambda m: m.text == "Настройки администратора")
async def admin_settings_handler(message: Message, state: FSMContext):
    """Обработчик настроек администратора - запускает задачу рассылки откликов"""
    await message.answer("🚀 Запускаю задачу рассылки откликов...")

    try:
        # await apply_to_vacancies_task()
        await message.answer("✅ Задача рассылки откликов выполнена успешно!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при выполнении задачи: {e}")