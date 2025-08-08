# celery_worker.py
"""
Запуск Celery worker:
    python celery_worker.py

Заметки:
- На Windows нужен pool=solo (prefork не поддерживается).
- Все параметры можно менять в argv ниже.
"""
import os
import platform
from src.celery_app import celery_app

if __name__ == "__main__":
    argv = [
        "-A", "src.celery_app.celery_app",
        "worker",
        "-l", "INFO",
        "-Q", "high,normal,low,retry",
        "--concurrency=4",
    ]

    # Windows: нужен solo pool
    if os.name == "nt" or platform.system().lower().startswith("win"):
        argv += ["--pool=solo"]

    celery_app.start(argv)
