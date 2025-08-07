# src/celery_app.py
"""
Улучшенная конфигурация Celery с очередями, мониторингом и обработкой ошибок
"""
import os
import logging
from celery import Celery, signals
from celery.schedules import crontab
from kombu import Queue, Exchange
from datetime import datetime

from src.config import config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Создание приложения Celery
celery_app = Celery(
    "hhbot",
    broker=config.redis.dsn,
    backend=config.redis.dsn,
)

# Настройки Celery
celery_app.conf.update(
    # Временная зона
    timezone="Europe/Moscow",
    enable_utc=True,

    # Сериализация
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    result_expires=3600 * 24,  # Результаты хранятся 24 часа

    # Настройки воркеров
    worker_prefetch_multiplier=1,  # Воркер берет по одной задаче за раз
    worker_max_tasks_per_child=50,  # Рестарт воркера после 50 задач (против memory leaks)
    worker_disable_rate_limits=False,  # Включаем rate limiting
    worker_max_memory_per_child=200000,  # Максимум 200MB на воркера

    # Обработка задач
    task_reject_on_worker_lost=True,  # Отклоняем задачи при потере воркера
    task_acks_late=True,  # Подтверждение после выполнения
    task_reject_on_worker_lost=True,  # Переотправка задач при сбое воркера

    # Retry настройки
    task_default_retry_delay=60,  # Задержка между повторами (60 сек)
    task_max_retries=3,  # Максимум 3 повтора

    # Мониторинг
    worker_send_task_events=True,  # Отправка событий воркера
    task_send_sent_event=True,  # Отправка событий задач
    worker_hijack_root_logger=False,  # Не захватываем root logger

    # Результаты
    result_backend_transport_options={
        'master_name': 'mymaster',
        'visibility_timeout': 3600,
    },

    # Маршрутизация задач по очередям
    task_routes={
        # Основная обработка резюме - высокий приоритет
        'src.workers.resume_processor.*': {
            'queue': 'resume_processing',
            'routing_key': 'resume.process',
            'priority': 8
        },

        # Поиск вакансий - средний приоритет
        'src.workers.vacancy_scraper.*': {
            'queue': 'vacancy_scraping',
            'routing_key': 'vacancy.scrape',
            'priority': 6
        },

        # Генерация писем - высокий приоритет (AI задачи)
        'src.workers.letter_generator.*': {
            'queue': 'letter_generation',
            'routing_key': 'letter.generate',
            'priority': 7
        },

        # Отправка откликов - критический приоритет
        'src.workers.application_sender.*': {
            'queue': 'application_sending',
            'routing_key': 'application.send',
            'priority': 9
        },

        # Уведомления - высокий приоритет
        'src.workers.notification_sender.*': {
            'queue': 'notifications',
            'routing_key': 'notification.send',
            'priority': 8
        },

        # Аналитика - низкий приоритет
        'src.workers.analytics_collector.*': {
            'queue': 'analytics',
            'routing_key': 'analytics.collect',
            'priority': 3
        },

        # Очистка - очень низкий приоритет
        'src.workers.cleanup_worker.*': {
            'queue': 'maintenance',
            'routing_key': 'maintenance.cleanup',
            'priority': 1
        },
    },

    # Настройка очередей по умолчанию
    task_default_queue='default',
    task_default_exchange='default',
    task_default_exchange_type='direct',
    task_default_routing_key='default',
)

# Определение exchanges
default_exchange = Exchange('default', type='direct')
resume_exchange = Exchange('resume_processing', type='direct')
vacancy_exchange = Exchange('vacancy_scraping', type='direct')
letter_exchange = Exchange('letter_generation', type='direct')
application_exchange = Exchange('application_sending', type='direct')
notification_exchange = Exchange('notifications', type='direct')
analytics_exchange = Exchange('analytics', type='direct')
maintenance_exchange = Exchange('maintenance', type='direct')

# Настройка очередей с приоритетами и дополнительными параметрами
celery_app.conf.task_queues = (
    # Обработка резюме - основная очередь
    Queue('resume_processing',
          exchange=resume_exchange,
          routing_key='resume.process',
          queue_arguments={
              'x-max-priority': 10,  # Поддержка приоритетов
              'x-message-ttl': 3600000,  # TTL сообщений (1 час)
              'x-max-length': 1000,  # Максимум 1000 задач в очереди
          }),

    # Поиск вакансий
    Queue('vacancy_scraping',
          exchange=vacancy_exchange,
          routing_key='vacancy.scrape',
          queue_arguments={
              'x-max-priority': 10,
              'x-message-ttl': 1800000,  # TTL 30 минут
              'x-max-length': 500,
          }),

    # Генерация писем через AI
    Queue('letter_generation',
          exchange=letter_exchange,
          routing_key='letter.generate',
          queue_arguments={
              'x-max-priority': 10,
              'x-message-ttl': 900000,  # TTL 15 минут (AI задачи должны быть быстрыми)
              'x-max-length': 200,
          }),

    # Отправка откликов - критическая очередь
    Queue('application_sending',
          exchange=application_exchange,
          routing_key='application.send',
          queue_arguments={
              'x-max-priority': 10,
              'x-message-ttl': 600000,  # TTL 10 минут
              'x-max-length': 100,
          }),

    # Уведомления пользователям
    Queue('notifications',
          exchange=notification_exchange,
          routing_key='notification.send',
          queue_arguments={
              'x-max-priority': 10,
              'x-message-ttl': 7200000,  # TTL 2 часа
              'x-max-length': 1000,
          }),

    # Аналитика и статистика
    Queue('analytics',
          exchange=analytics_exchange,
          routing_key='analytics.collect',
          queue_arguments={
              'x-max-priority': 5,
              'x-message-ttl': 86400000,  # TTL 24 часа
              'x-max-length': 100,
          }),

    # Обслуживание и очистка
    Queue('maintenance',
          exchange=maintenance_exchange,
          routing_key='maintenance.cleanup',
          queue_arguments={
              'x-max-priority': 3,
              'x-message-ttl': 86400000,  # TTL 24 часа
              'x-max-length': 50,
          }),

    # Очередь по умолчанию
    Queue('default',
          exchange=default_exchange,
          routing_key='default'),
)

# Расписание периодических задач
celery_app.conf.beat_schedule = {
    # Основная задача - обработка резюме каждый час
    'process-resumes-hourly': {
        'task': 'src.workers.resume_processor.process_all_active_resumes_task',
        'schedule': crontab(minute=0),  # Каждый час в 0 минут
        'options': {
            'queue': 'resume_processing',
            'priority': 9
        },
        'kwargs': {
            'task_type': 'scheduled',
            'max_resumes': 100,  # Ограничение для scheduled задач
        }
    },

    # Отправка уведомлений каждые 10 минут
    'send-pending-notifications': {
        'task': 'src.workers.notification_sender.send_pending_notifications_task',
        'schedule': crontab(minute='*/10'),  # Каждые 10 минут
        'options': {
            'queue': 'notifications',
            'priority': 8
        }
    },

    # Обновление статусов откликов каждые 30 минут
    'update-application-statuses': {
        'task': 'src.workers.application_sender.update_application_statuses_task',
        'schedule': crontab(minute='*/30'),  # Каждые 30 минут
        'options': {
            'queue': 'application_sending',
            'priority': 7
        }
    },

    # Сбор аналитики каждые 2 часа
    'collect-analytics': {
        'task': 'src.workers.analytics_collector.collect_daily_analytics_task',
        'schedule': crontab(minute=0, hour='*/2'),  # Каждые 2 часа
        'options': {
            'queue': 'analytics',
            'priority': 4
        }
    },

    # Ежедневные отчеты в 9:00
    'send-daily-reports': {
        'task': 'src.workers.notification_sender.send_daily_reports_task',
        'schedule': crontab(hour=9, minute=0),  # Каждый день в 9:00
        'options': {
            'queue': 'notifications',
            'priority': 6
        }
    },

    # Еженедельные отчеты по понедельникам в 10:00
    'send-weekly-reports': {
        'task': 'src.workers.notification_sender.send_weekly_reports_task',
        'schedule': crontab(hour=10, minute=0, day_of_week=1),  # Понедельник 10:00
        'options': {
            'queue': 'notifications',
            'priority': 5
        }
    },

    # Очистка старых данных каждый день в 3:00
    'cleanup-old-data': {
        'task': 'src.workers.cleanup_worker.cleanup_old_data_task',
        'schedule': crontab(hour=3, minute=0),  # Каждый день в 3:00
        'options': {
            'queue': 'maintenance',
            'priority': 2
        },
        'kwargs': {
            'days_to_keep': 30,  # Храним данные 30 дней
        }
    },

    # Очистка логов каждую неделю
    'cleanup-logs': {
        'task': 'src.workers.cleanup_worker.cleanup_logs_task',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),  # Воскресенье 2:00
        'options': {
            'queue': 'maintenance',
            'priority': 1
        }
    },
}

# Автоимпорт задач
celery_app.autodiscover_tasks([
    'src.workers.resume_processor',
    'src.workers.vacancy_scraper',
    'src.workers.letter_generator',
    'src.workers.application_sender',
    'src.workers.notification_sender',
    'src.workers.analytics_collector',
    'src.workers.cleanup_worker',
])


# Hooks для логирования и мониторинга

@signals.task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Выполняется перед запуском задачи"""
    logger.info(f"Starting task {task.name} [ID: {task_id}] with args={args}, kwargs={kwargs}")


@signals.task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None,
                         kwargs=None, retval=None, state=None, **kwds):
    """Выполняется после завершения задачи"""
    logger.info(f"Task {task.name} [ID: {task_id}] finished with state: {state}")


@signals.task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, traceback=None, einfo=None, **kwds):
    """Выполняется при повторе задачи"""
    logger.warning(f"Task {sender.name} [ID: {task_id}] retry: {reason}")


@signals.task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """Выполняется при ошибке в задаче"""
    logger.error(f"Task {sender.name} [ID: {task_id}] FAILED: {exception}")

    # Здесь можно добавить отправку критических уведомлений админам
    # или сохранение в базу для мониторинга


@signals.worker_ready.connect
def worker_ready_handler(sender=None, **kwds):
    """Выполняется когда воркер готов к работе"""
    logger.info(f"Worker {sender.hostname} is ready")


@signals.worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwds):
    """Выполняется при выключении воркера"""
    logger.info(f"Worker {sender.hostname} is shutting down")


# Дополнительные настройки для продакшена
if os.getenv('ENVIRONMENT') == 'production':
    # В продакшене используем более консервативные настройки
    celery_app.conf.update(
        worker_max_tasks_per_child=25,  # Меньше задач на воркера
        worker_max_memory_per_child=150000,  # Меньше памяти
        result_expires=1800,  # Результаты хранятся 30 минут
    )

    # Добавляем дополнительные очереди для продакшена
    celery_app.conf.task_queues += (
        Queue('high_priority',
              exchange=default_exchange,
              routing_key='high_priority',
              queue_arguments={'x-max-priority': 10}),

        Queue('low_priority',
              exchange=default_exchange,
              routing_key='low_priority',
              queue_arguments={'x-max-priority': 1}),
    )


# Middleware для мониторинга производительности
@celery_app.task(bind=True)
def debug_task(self):
    """Задача для отладки и мониторинга"""
    logger.info(f'Debug task executed: {self.request!r}')
    return f'Debug task completed at {datetime.now()}'


# Экспорт для использования в других модулях
__all__ = ['celery_app']