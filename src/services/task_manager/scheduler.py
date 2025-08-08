# src/services/task_manager/scheduler.py

from typing import Iterable

from src.celery_app import celery_app
from src.config.celery_config import config as celery_cfg

# Импортируем таски, если хотим прямые вызовы .delay()
from src.workers.application_sender_worker import schedule_bulk_apply, apply_for_resume


def enqueue_bulk_apply_for_user(user_id: int) -> str:
    """
    Вызов из бота/админки/вебхука — поставить задачу верхнего уровня для пользователя.
    Возвращает id Celery-задачи.
    """
    result = schedule_bulk_apply.apply_async(
        kwargs={"user_id": user_id},
        queue=celery_cfg.queues_high,
        routing_key="q.high",
    )
    return result.id


def enqueue_apply_for_resumes(resume_ids: Iterable[str]) -> list[str]:
    """
    Массовая постановка задач для набора резюме.
    """
    task_ids: list[str] = []
    for rid in resume_ids:
        res = apply_for_resume.apply_async(
            kwargs={"resume_id": rid},
            queue=celery_cfg.queues_normal,
            routing_key="q.normal",
        )
        task_ids.append(res.id)
    return task_ids
