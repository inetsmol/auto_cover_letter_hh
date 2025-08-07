# src/celery_init.py
import asyncio

from celery import Celery
from celery.schedules import crontab
from src.config import config
from src.tasks.apply import apply_to_vacancies_task

celery_app = Celery(
    "hhbot",
    broker=config.redis.dsn,
    backend=config.redis.dsn
)

celery_app.conf.update(
    timezone="Europe/Moscow",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    'send-auto-responses-every-20-min': {
        'task': 'src.celery_init.apply_to_vacancies_task_sync',
        'schedule': crontab(minute='*/20'),  # каждые 20 минут
    },
}


@celery_app.task
def apply_to_vacancies_task_sync():
    """
    Синхронный адаптер для Celery (Celery не умеет напрямую асинхронные таски).
    """
    asyncio.run(apply_to_vacancies_task())
