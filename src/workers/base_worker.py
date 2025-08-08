# src/workers/base_worker.py

import logging
from celery import Task
from contextlib import asynccontextmanager

from src.db.init import init_db, close_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def task_context():
    """
    Общий async-контекст для задач:
    - инициализация БД (Tortoise)
    - здесь же можно открывать/закрывать клиентов API, кэши и т.п.
    """
    await init_db()
    try:
        yield
    finally:
        await close_db()


class BaseTask(Task):
    """
    Базовый класс задач Celery: ретраи, бэкофф, логирование.
    """
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 15}
    retry_backoff = True
    retry_backoff_max = 60
    retry_jitter = True

    def on_success(self, retval, task_id, args, kwargs):
        logger.info("[OK] %s(%s) -> %s", self.name, task_id, {"args": args, "kwargs": kwargs})

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error("[FAIL] %s(%s): %s", self.name, task_id, exc, exc_info=einfo)
