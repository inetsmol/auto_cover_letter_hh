# src/bot/handlers/resume/list_resumes.py
from aiogram import Router, F
from aiogram.types import CallbackQuery

from src.bot.keyboards.resume_management import resumes_list_menu, resume_main_menu
from src.models import Resume

router = Router()

@router.callback_query(F.data == "menu:resumes")
async def my_resumes_callback(call: CallbackQuery, state):
    await call.message.delete()

    user_id = call.from_user.id
    resumes = await Resume.filter(user_id=user_id).all()

    if not resumes:
        await call.message.answer(
            "У вас пока нет добавленных резюме.\n\n"
            "Используйте кнопку 'Добавить резюме' чтобы добавить первое резюме.",
            reply_markup=resume_main_menu()
        )
        await call.answer()
        return

    # Формируем список кнопок по каждому резюме
    buttons_data = [
        {"id": r.id, "title": (r.resume_json or {}).get('title', 'Без названия')}
        for r in resumes
    ]
    await call.message.answer(
        "📄 Ваши резюме:",
        reply_markup=resumes_list_menu(buttons_data)
    )
    await call.answer()
