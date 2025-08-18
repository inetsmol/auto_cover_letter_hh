# src/celery_app.py
from celery import Celery
from kombu import Queue
from celery.schedules import crontab

from src.config import config

celery_app = Celery(
    "hh_bot",
    broker=config.redis.dsn,
    backend=config.redis.dsn,
    include=["src.workers.apply"],
)

celery_app.conf.timezone = "Europe/Moscow"
celery_app.conf.enable_utc = True
celery_app.conf.task_time_limit = 60       # hard limit
celery_app.conf.task_soft_time_limit = 40  # soft limit

# Очереди
celery_app.conf.task_queues = (
    Queue("celery"),
    Queue("free"),
)
celery_app.conf.task_default_queue = "celery"

# Расписания
celery_app.conf.beat_schedule = {
    "paid-hourly": {
        "task": "src.workers.apply.run_paid_hourly",
        "schedule": crontab(minute=0),
    },
    "free-daily-12msk": {
        "task": "src.workers.apply.run_free_daily",
        "schedule": crontab(minute=0, hour=12),
        "options": {"queue": "free"},
    },
}
