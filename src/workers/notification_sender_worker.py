# src/workers/notification_sender_worker.py
import asyncio
import logging

from src.celery_app import celery_app
from src.db.init import init_db, close_db
from src.tasks.notifications import notification_task
from src.utils.selectors import get_active_user_ids_for_notification

logger = logging.getLogger(__name__)


@celery_app.task(name="src.workers.notification_sender_worker.run_notifications_daily")
def run_notifications_daily():
    async def _run():
        await init_db()
        try:
            user_ids = await get_active_user_ids_for_notification()
            logger.info("[notifications_daily] users=%d -> %s", len(user_ids), user_ids)
            for uid in user_ids:
                await notification_task(uid)
        finally:
            await close_db()

    asyncio.run(_run())


@celery_app.task(name="src.workers.notification_sender_worker.run_notifications_every_15m")
def run_notifications_every_15m():
    async def _run():
        await init_db()
        try:
            user_ids = await get_active_user_ids_for_notification()
            logger.info("[notifications_15m] users=%d -> %s", len(user_ids), user_ids)
            for uid in user_ids:
                await notification_task(uid)
        finally:
            await close_db()

    asyncio.run(_run())
