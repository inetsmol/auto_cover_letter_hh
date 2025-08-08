# src/services/application/result_service.py
from src.models.application_result import ApplicationResult


async def save_application_result(user_id: str, resume_id: str, total_vacancies: int, sent_applications: int, skipped_tests: list):
    """
    Сохраняет статистику отправки откликов в БД.
    """
    result = await ApplicationResult.create(
        user_id=user_id,
        resume_id=resume_id,
        total_vacancies=total_vacancies,
        sent_applications=sent_applications,
        skipped_tests=skipped_tests
    )
    return result
