# celery_beat.py
"""
Запуск Celery beat:
    python celery_beat.py
"""

from datetime import timedelta
from src.celery_app import celery_app

# Каждые 30 секунд ставим задачу schedule_bulk_apply
celery_app.conf.beat_schedule = {
    "bulk-apply-every-30sec": {
        "task": "workers.application_sender.schedule_bulk_apply",
        "schedule": timedelta(seconds=30),
        "args": [],
        "kwargs": {"user_id": None},  # None = для всех активных резюме
        "options": {"queue": "high", "routing_key": "q.high"},
    },
}

if __name__ == "__main__":
    argv = [
        "-A", "src.celery_app.celery_app",
        "beat",
        "-l", "INFO",
    ]
    celery_app.start(argv)
