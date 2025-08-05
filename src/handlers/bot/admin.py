from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.tasks.apply import apply_to_vacancies_task

router = Router()


@router.message(lambda m: m.text == "Настройки администратора")
async def add_resume_start(message: Message, state: FSMContext):
    await apply_to_vacancies_task()
