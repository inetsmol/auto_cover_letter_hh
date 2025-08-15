from src.models import User, Resume
from src.services.hh.client import hhc
from src.services.resume.parser import extract_keywords


async def add_resume_task(user_id, resume_id):
    # 1) Тянем резюме из HH API
    try:
        # resume_json = await hh_client.get_resume(resume_id)
        resume_json = await hhc.get_resume(resume_id)
    except Exception as e:
        raise f"❗️Ошибка при получении резюме: {e}\n Проверьте доступность резюме и корректность ссылки."

    # 2) Извлекаем ключевые слова из заголовка
    positive_keywords = extract_keywords(resume_json.get("title", ""))

    # 3) Сохраняем/обновляем в БД (привязываем к пользователю)
    user = await User.get_or_none(id=user_id)
    resume, created = await Resume.get_or_create(
        id=resume_id,
        defaults={
            "user": user,
            "resume_json": resume_json,
            "positive_keywords": positive_keywords,
        },
    )
    if not created:
        resume.user = user
        resume.resume_json = resume_json
        resume.positive_keywords = positive_keywords
        await resume.save()

    return resume, positive_keywords