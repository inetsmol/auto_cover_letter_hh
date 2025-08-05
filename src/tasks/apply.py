# src/tasks/apply.py
import logging
import asyncio
import httpx

from src.ai.openai_api import generate_cover_letter
from src.celery_init import celery_app
from src.hh_auth import get_headers

from src.models import Resume
from src.services.resume import extract_resume_from_resume_json
from src.services.vacancies import search_similar_vacancies, get_vacancies_by_id, extract_job_description_from_hh_api

logger = logging.getLogger("apply_vacancies")


async def apply_to_vacancy(resume_id: str, vacancy_id: str, message: str) -> bool:
    """
    Откликается на вакансию от имени активного резюме.
    """
    url = "https://api.hh.ru/negotiations"
    headers = await get_headers()
    data = {
        "vacancy_id": vacancy_id,
        "resume_id": resume_id,
        "message": message
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, data=data)
            response.raise_for_status()
            logger.info(f"Отклик на вакансию {vacancy_id} успешно отправлен.")
            return True
    except httpx.HTTPStatusError as e:
        logger.error(f"Ошибка HTTP при отклике на {vacancy_id}: {e.response.status_code} - {e.response.text}")
        return False
    except httpx.RequestError as e:
        logger.error(f"Ошибка запроса при отклике на {vacancy_id}: {e}")
        return False
    except Exception as e:
        logger.exception(f"Неожиданная ошибка при отклике на {vacancy_id}: {e}")
        return False


async def process_vacancy(resume_id, vacancy_id, resume_text):
    """
    Обрабатывает одну вакансию: скачивает детали, формирует письмо, откликается.
    """
    try:
        vacancy = await get_vacancies_by_id(vacancy_id)
        job_description_text = extract_job_description_from_hh_api(vacancy)
        cover_letter = await generate_cover_letter(resume_text, job_description_text)
        ok = await apply_to_vacancy(resume_id=resume_id, vacancy_id=vacancy_id, message=cover_letter)
        await asyncio.sleep(2)  # Пауза между откликами
        return ok
    except Exception as e:
        logger.exception(f"Ошибка при обработке вакансии {vacancy_id} для резюме {resume_id}: {e}")
        return False


async def apply_to_vacancies_task():
    """
    Находит все активные резюме и массово откликается на релевантные вакансии.
    """
    resumes = await Resume.filter(
        status="active",
        user__user_status="active"
    )

    for item in resumes:
        resume_id = item.id
        keywords = item.keywords
        resume_json = item.resume_json
        resume_text = extract_resume_from_resume_json(resume_json)

        logger.info(f"Обрабатываем резюме: {resume_id}")
        vacancies = await search_similar_vacancies(text=keywords, resume_id=resume_id, per_page=25)
        if not vacancies:
            logger.info(f"Вакансии не найдены для резюме {resume_id}")
            continue

        vacancy_ids_with_tests = [v['id'] for v in vacancies if v.get('has_test')]
        vacancy_ids = [v['id'] for v in vacancies if not v.get('has_test')]
        logger.info(f"Пропущено из-за тестов: {len(vacancy_ids_with_tests)} вакансий")

        results = []
        for vacancy_id in vacancy_ids:
            result = await process_vacancy(resume_id, vacancy_id, resume_text)
            results.append(result)

        logger.info(f"Откликов отправлено: {sum(results)} из {len(vacancy_ids)} для резюме {resume_id}")


@celery_app.task
def apply_to_vacancies_task_sync():
    """
    Синхронный адаптер для Celery (Celery не умеет напрямую асинхронные таски).
    """
    asyncio.run(apply_to_vacancies_task())
