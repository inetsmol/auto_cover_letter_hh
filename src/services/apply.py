# src/services/apply.py
import asyncio
import logging

from src.ai.openai_api import generate_cover_letter
from src.models import Resume
from src.services.hh_client import hh_client
from src.services.resume import extract_resume_from_resume_json

logging.basicConfig(
    level=logging.INFO,  # или logging.DEBUG
    format="%(asctime)s %(levelname)s [%(name)s]: %(message)s"
)

logger = logging.getLogger(__name__)


async def process_vacancy(resume_id, vacancy_id, resume_text):
    """
    Обрабатывает одну вакансию: скачивает детали, формирует письмо, откликается.
    """
    try:
        vacancy = await hh_client.get_vacancy(vacancy_id)
        if not vacancy:
            logger.error(f"Не удалось получить данные вакансии {vacancy_id}")
            return False

        job_description_text = hh_client.extract_job_description_from_vacancy(vacancy)
        cover_letter = await generate_cover_letter(resume_text, job_description_text)
        ok = await hh_client.apply_to_vacancy(resume_id=resume_id, vacancy_id=vacancy_id, message=cover_letter)
        await asyncio.sleep(2)
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
        vacancies = await hh_client.search_similar_vacancies(text=keywords, resume_id=resume_id, per_page=25)
        if not vacancies:
            logger.info(f"Вакансии не найдены для резюме {resume_id}")
            continue

        vacancy_ids_with_tests = [v['id'] for v in vacancies if v.get('has_test')]
        vacancy_ids = [v['id'] for v in vacancies if not v.get('has_test')]
        logger.info(f"Найдено вакансий: {vacancy_ids}")
        logger.info(f"Пропущено из-за тестов: {len(vacancy_ids_with_tests)} вакансий")

        results = []
        for vacancy_id in vacancy_ids:
            result = await process_vacancy(resume_id, vacancy_id, resume_text)
            results.append(result)

        logger.info(f"Откликов отправлено: {sum(results)} из {len(vacancy_ids)} для резюме {resume_id}")
