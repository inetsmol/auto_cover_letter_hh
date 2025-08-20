# src/tasks/apply.py
from typing import Optional

from hh_api.client import HHClient

from src.config import config
from src.db.init import init_db, close_db
from src.models import Resume, ApplicationResult
from src.services.ai.cover_letter_service import generate_cover_letter
from src.services.hh.auth.token_manager import tm
from src.services.resume.parser import extract_resume_description_from_json
from src.services.vacancy.parser import extract_job_description_from_vacancy

from src.services.ai.openai_pool import (
    setup as ai_setup,
    teardown as ai_teardown,
    OpenAISettings,
)


async def apply_for_resume_task(resume_id: str, cap: Optional[int] = None):

    resume = await Resume.get(id=resume_id)
    user_id = resume.user_id

    hhc = HHClient(tm=tm, user_agent=config.hh.user_agent, subject=user_id)

    text = getattr(resume, "keywords", "") or ""
    negative_keywords = resume.negative_keywords
    resume_json = await hhc.get_resume(resume_id)
    resume_text = extract_resume_description_from_json(resume_json)

    try:
        items = await hhc.search_similar_vacancies(resume_id=resume_id, text=text, per_page=100)
    except Exception:
        raise
    sent = 0
    skipped = []

    for item in items:
        vacancy_id = item.get('id')
        if cap is not None and sent >= cap:
            break
        if item.get('has_test'):
            skipped.append(vacancy_id)
            continue
        vacancy = await hhc.get_vacancy(vacancy_id=vacancy_id)
        # print(f'vacancy: {vacancy}')
        # Извлекаем описание вакансии из JSON
        job_description_text = extract_job_description_from_vacancy(vacancy)
        # print(f'job_description_text: {job_description_text}')
        cover_letter = await generate_cover_letter(resume_text, job_description_text)
        # print(f"cover_letter: {cover_letter}")
        try:
            await hhc.apply_to_vacancy(
                resume_id=resume_id,
                vacancy_id=vacancy_id,
                message=cover_letter,
            )
        except Exception:
            raise
        sent += 1

    # Сохраняем краткий результат в ApplicationResult
    await ApplicationResult.create(
        user_id=user_id,
        resume_id=resume_id,
        total_vacancies=len(items),
        sent_applications=sent,
        skipped_tests=skipped,
    )
    return sent


async def _main(resume_id: str, cap: int = 2) -> None:
    await init_db()
    resume = await Resume.get(id=resume_id)
    user_id = resume.user_id
    text = getattr(resume, "keywords", "") or ""
    negative_keywords = resume.negative_keywords
    hhc = HHClient(tm=tm, user_agent=config.hh.user_agent, subject=user_id)

    items = await hhc.search_similar_vacancies(resume_id=resume_id, text=text, per_page=1)
    for item in items:
        vacancy_id = item.get('id')
        name = item.get('name')
        print(name)
        # print(item)

    await close_db()
    # print(f"text: {text}")
    # """
    # Тестовый запуск apply_for_resume_task:
    # - поднимаем пул OpenAI (фон. event loop + httpx),
    # - инициализируем Tortoise ORM,
    # - выполняем задачу, печатаем кол-во отправленных откликов,
    # - корректно закрываем ресурсы.
    # """
    # # 1) Инициализируем пул OpenAI (важно: до вызова apply_for_resume_task)
    # ai_setup(OpenAISettings(
    #     api_key=config.ai.openai_api_key.get_secret_value(),
    #     proxy_url=(config.ai.proxy_url or None),
    #     connect_timeout=15.0,
    #     read_timeout=60.0,
    #     pool_timeout=60.0,
    #     http2=True,
    # ))
    #
    # # 2) Инициализация БД (иначе будет ошибка default_connection is None)
    # await init_db()
    # try:
    #     sent = await apply_for_resume_task(resume_id, cap)
    #     # print(f"Отправлено откликов: {sent}")
    # finally:
    #     await close_db()
    #     ai_teardown()


if __name__ == "__main__":
    import asyncio
    re_id = "33d54f44ff0e2607650039ed1f6471796e654d"
    cap = 2
    asyncio.run(_main(re_id, cap))