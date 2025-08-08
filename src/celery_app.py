from celery import Celery
from kombu import Queue, Exchange

from src.config.celery_config import config as celery_cfg

celery_app = Celery("auto_cover_letter_hh")

celery_app.conf.update(
    broker_url=celery_cfg.broker_url,
    result_backend=celery_cfg.result_backend,
    task_default_queue=celery_cfg.task_default_queue,
    task_acks_late=celery_cfg.task_acks_late,
    worker_prefetch_multiplier=celery_cfg.worker_prefetch_multiplier,
    task_track_started=celery_cfg.task_track_started,
    task_time_limit=celery_cfg.task_time_limit,
    task_soft_time_limit=celery_cfg.task_soft_time_limit,
    task_default_rate_limit=celery_cfg.task_default_rate_limit,
)

# Очереди/экченджи
exchange = Exchange("aclh", type="direct")
celery_app.conf.task_queues = (
    Queue(celery_cfg.queues_high,   exchange=exchange, routing_key="q.high"),
    Queue(celery_cfg.queues_normal, exchange=exchange, routing_key="q.normal"),
    Queue(celery_cfg.queues_low,    exchange=exchange, routing_key="q.low"),
    Queue(celery_cfg.queues_retry,  exchange=exchange, routing_key="q.retry"),
)

# Роутинг тасок
celery_app.conf.task_routes = {
    "workers.application_sender.*": {
        "queue": celery_cfg.queues_normal,
        "routing_key": "q.normal",
    },
}

# Автодискавер
celery_app.autodiscover_tasks(
    packages=["src.workers"],
    related_name=None,
)
