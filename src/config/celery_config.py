# src/config/celery_config.py

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.config import config


class CeleryConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CELERY_", env_file=".env", extra="ignore")

    broker_url: str = config.redis.dsn
    result_backend: str = config.redis.dsn

    # Общие настройки
    task_default_queue: str = "default"
    task_acks_late: bool = True
    worker_prefetch_multiplier: int = 1
    task_track_started: bool = True
    task_time_limit: int = 60 * 10           # 10 минут
    task_soft_time_limit: int = 60 * 8       # 8 минут
    task_default_rate_limit: str | None = None

    # Определим именованные очереди
    queues_high: str = "high"
    queues_normal: str = "normal"
    queues_low: str = "low"
    queues_retry: str = "retry"


config = CeleryConfig()
