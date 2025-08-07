import logging
from functools import wraps
from src.models import Resume

def with_resume_from_callback(handler):
    """
    Декоратор для aiogram-хендлеров.
    Достаёт resume_id из callback_data и резюме из базы.
    Если resume не найден — выводит сообщение и завершает хендлер.
    Передаёт resume_id и resume в аргументы хендлера.
    Также удаляет исходное сообщение с меню.
    """
    @wraps(handler)
    async def wrapper(call, *args, **kwargs):
        # Удалить исходное сообщение (если ещё не удалено)
        try:
            await call.message.delete()
        except Exception:
            pass
        try:
            resume_id = call.data.split(":")[-1]
        except Exception:
            logging.exception("Некорректный callback data: %r", call.data)
            await call.message.answer("Что-то пошло не так. Попробуйте ещё раз или выберите пункт меню заново.")
            await call.answer()
            return

        resume = await Resume.get_or_none(id=resume_id)
        if not resume:
            await call.message.answer("Резюме не найдено.")
            await call.answer()
            return

        # Передаём resume_id и resume в хендлер
        return await handler(call, resume_id, resume, *args, **kwargs)
    return wrapper
