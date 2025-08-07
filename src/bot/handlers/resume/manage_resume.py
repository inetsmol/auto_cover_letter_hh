# src/bot/handlers/resume/manage_resume.py
from aiogram import Router, F
from aiogram.types import CallbackQuery

from src.bot.keyboards.resume_management import manage_resume_menu, resumes_list_menu
from src.models import Resume

router = Router()

@router.callback_query(F.data.regexp(r"^resume:manage:(.+)"))
async def manage_resume_callback(call: CallbackQuery, state):
    await call.message.delete()

    resume_id = call.data.split(":")[-1]
    resume = await Resume.get_or_none(id=resume_id)

    if not resume:
        await call.message.answer("Резюме не найдено.")
        await call.answer()
        return

    title = (resume.resume_json or {}).get('title', 'Без названия')
    positive_keywords = ', '.join(resume.positive_keywords or [])
    negative_keywords = ', '.join(resume.negative_keywords or [])
    status = resume.status

    text = (
        f"<b>{title}</b>\n"
        f"ID: <code>{resume.id}</code>\n"
        f"Статус: {status}\n"
        f"Ключевые слова: {positive_keywords or 'нет'}\n"
    )
    if negative_keywords:
        text += f"Исключения: {negative_keywords}\n"

    await call.message.answer(text, reply_markup=manage_resume_menu(resume_id))
    await call.answer()


@router.callback_query(F.data.regexp(r"^resume:delete:(.+)"))
async def delete_resume_handler(call: CallbackQuery, state):
    await call.message.delete()

    resume_id = call.data.split(":")[-1]
    resume = await Resume.get_or_none(id=resume_id)

    if not resume:
        await call.message.answer("Резюме не найдено или уже удалено.")
        await call.answer()
        return

    user_id = call.from_user.id
    await resume.delete()

    # После удаления возвращаем пользователя к списку резюме
    resumes = await Resume.filter(user_id=user_id).all()
    if resumes:
        buttons_data = [
            {"id": r.id, "title": (r.resume_json or {}).get('title', 'Без названия')}
            for r in resumes
        ]
        await call.message.answer(
            "Резюме удалено.\n\nВаши резюме:",
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
async def change_status_handler(call: CallbackQuery, state):
    await call.message.delete()

    resume_id = call.data.split(":")[-1]
    resume = await Resume.get_or_none(id=resume_id)

    if not resume:
        await call.message.answer("Резюме не найдено.")
        await call.answer()
        return

    # Переключаем статус
    new_status = "inactive" if resume.status == "active" else "active"
    resume.status = new_status
    await resume.save()

    status_emoji = "✅" if new_status == "active" else "⏸"
    await call.message.answer(
        f"{status_emoji} Статус резюме изменён на: <b>{new_status}</b>.",
        reply_markup=manage_resume_menu(resume_id)
    )
    await call.answer()
