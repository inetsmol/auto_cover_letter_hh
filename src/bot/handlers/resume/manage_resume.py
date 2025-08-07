# src/bot/handlers/resume/manage_resume.py
from aiogram import Router, F
from aiogram.types import CallbackQuery

from src.bot.keyboards.resume_management import manage_resume_menu, resumes_list_menu
from src.models import Resume
from src.utils.decorators import with_resume_from_callback
from src.utils.formatters import format_resume_card

router = Router()

@router.callback_query(F.data.regexp(r"^resume:manage:(.+)"))
@with_resume_from_callback
async def manage_resume_callback(call: CallbackQuery, resume_id, resume, state):
    await call.message.answer(
        format_resume_card(resume),
        reply_markup=manage_resume_menu(resume_id)
    )
    await call.answer()


@router.callback_query(F.data.regexp(r"^resume:delete:(.+)"))
@with_resume_from_callback
async def delete_resume_handler(call: CallbackQuery, resume_id, resume, state):
    user_id = call.from_user.id
    await resume.delete()

    # После удаления возвращаем пользователя к списку резюме
    resumes = await Resume.filter(user_id=user_id).all()
    if resumes:
        buttons_data = [
            {"id": r.id, "title": (r.resume_json or {}).get('title', 'Без названия')}
            for r in resumes
        ]
        await call.message.answer("Резюме удалено.")
        await call.message.answer(
            "Ваши резюме:",
            reply_markup=resumes_list_menu(buttons_data)
        )
    else:
        from src.bot.keyboards.resume_management import resume_main_menu
        await call.message.answer(
            "Резюме удалено. У вас больше нет добавленных резюме.",
            reply_markup=resume_main_menu()
        )
    await call.answer()


@router.callback_query(F.data.regexp(r"^resume:status:(.+)"))
@with_resume_from_callback
async def change_status_handler(call: CallbackQuery, resume_id, resume, state):

    # Переключаем статус
    new_status = "inactive" if resume.status == "active" else "active"
    resume.status = new_status
    await resume.save()

    status_emoji = "✅" if new_status == "active" else "📁"
    await call.message.answer(
        f"{status_emoji} Статус резюме изменён на: <b>{'Активно' if new_status == 'active' else 'В архиве'}</b>."
    )

    await call.message.answer(
        format_resume_card(resume),
        reply_markup=manage_resume_menu(resume_id)
    )
    await call.answer()
