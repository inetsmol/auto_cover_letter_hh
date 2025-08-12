# src/workers/application_sender_worker.py
from __future__ import annotations

import asyncio
import logging
import os
import platform
from typing import Iterable, Optional

from celery import shared_task
from tortoise import Tortoise
from tortoise.expressions import Q
from tortoise.timezone import now

from src.celery_app import celery_app
from src.db.config import TORTOISE_ORM
from src.models import (
    Resume,
    Subscription,
    Plan,
    SubscriptionStatus,
    ApplicationHistory,
    ApplicationStatus,
)
from src.services.ai.cover_letter_service import generate_cover_letter
from src.services.hh_client import hh_client
from src.services.task_manager.result_processor import save_run_result
from src.services.notification.telegram_notifier import send_processing_summary

logger = logging.getLogger(__name__)

# Очереди
QUEUE_HIGH = "high"
QUEUE_NORMAL = "normal"
QUEUE_LOW = "low"

TASK_NS = "workers.application_sender"
_ORM_READY = False


async def init_orm() -> None:
    global _ORM_READY
    if _ORM_READY:
        return
    await Tortoise.init(config=TORTOISE_ORM)
    _ORM_READY = True
    logger.info("Tortoise ORM initialized.")


def run_async(coro):
    async def _runner():
        await init_orm()
        return await coro
    return asyncio.run(_runner())


# ==========================
#      ПЛАНИРОВАНИЕ
# ==========================

@shared_task(bind=True, name=f"{TASK_NS}.schedule_bulk_apply")
def schedule_bulk_apply(self, user_id: Optional[int] = None) -> None:
    run_async(_schedule_bulk_apply_async(user_id=user_id))


async def _schedule_bulk_apply_async(user_id: Optional[int] = None) -> None:
    await init_orm()

    if user_id is not None:
        user_ids = [user_id]
        run_type = "manual"
    else:
        active_q = Q(status=SubscriptionStatus.ACTIVE) & (Q(expires_at=None) | Q(expires_at__gt=now()))
        user_ids = list(await Subscription.filter(active_q).values_list("user_id", flat=True))
        run_type = "bulk"

    for uid in user_ids:
        queue = await _queue_for_user(uid)
        enqueued = await _enqueue_user_resumes(uid, queue)

        # persist + notify
        try:
            await save_run_result(user_id=uid, run_type=run_type, resumes_enqueued=enqueued, meta={"queue": queue})
            await send_processing_summary(user_id=uid, run_type=run_type, resumes_enqueued=enqueued)
        except Exception:
            logger.exception("Persist/notify failed for user_id=%s", uid)


@shared_task(bind=True, name=f"{TASK_NS}.schedule_free_daily", queue=QUEUE_LOW)
def schedule_free_daily(self) -> None:
    run_async(_schedule_cohort_async(plans=[Plan.FREE], child_queue=QUEUE_LOW, run_type="free_daily"))


@shared_task(bind=True, name=f"{TASK_NS}.schedule_paid_hourly", queue=QUEUE_HIGH)
def schedule_paid_hourly(self) -> None:
    run_async(_schedule_cohort_async(plans=[Plan.PLUS, Plan.PRO], child_queue=QUEUE_HIGH, run_type="paid_hourly"))


async def _schedule_cohort_async(*, plans: Iterable[Plan], child_queue: str, run_type: str) -> None:
    await init_orm()
    active_q = Q(status=SubscriptionStatus.ACTIVE) & (Q(expires_at=None) | Q(expires_at__gt=now()))
    user_ids = list(await Subscription.filter(active_q, plan__in=list(plans)).values_list("user_id", flat=True))

    for uid in user_ids:
        enqueued = await _enqueue_user_resumes(uid, child_queue)
        try:
            await save_run_result(user_id=uid, run_type=run_type, resumes_enqueued=enqueued, meta={"queue": child_queue})
            await send_processing_summary(user_id=uid, run_type=run_type, resumes_enqueued=enqueued)
        except Exception:
            logger.exception("Persist/notify failed for user_id=%s", uid)


async def _enqueue_user_resumes(user_id: int, queue: str) -> int:
    """Ставит подзадачи apply_for_resume по активным резюме пользователя. Возвращает число задач."""
    resumes = list(await Resume.filter(user_id=user_id, is_active=True).values_list("id", flat=True))
    for rid in resumes:
        apply_for_resume.apply_async(args=[rid], queue=queue, routing_key=f"q.{queue}")
    logger.info("Enqueued %d resume(s) for user_id=%s -> queue=%s", len(resumes), user_id, queue)
    return len(resumes)


async def _queue_for_user(user_id: int) -> str:
    sub = await Subscription.get_or_none(user_id=user_id)
    if not sub or sub.status != SubscriptionStatus.ACTIVE:
        return QUEUE_LOW
    if sub.plan in (Plan.PLUS, Plan.PRO):
        return QUEUE_HIGH
    if sub.plan == Plan.FREE:
        return QUEUE_LOW
    return QUEUE_NORMAL


# ==========================
#  РЕЗЮМЕ → ВАКАНСИИ
# ==========================

@shared_task(bind=True, name=f"{TASK_NS}.apply_for_resume")
def apply_for_resume(self, resume_id: int) -> None:
    run_async(_apply_for_resume_async(resume_id))


async def _apply_for_resume_async(resume_id: int) -> None:
    await init_orm()

    resume = await Resume.get_or_none(id=resume_id)
    if not resume:
        logger.warning("Resume not found: %s", resume_id)
        return
    if getattr(resume, "is_active", True) is not True:
        logger.info("Resume inactive: %s", resume_id)
        return

    hh_resume_id = getattr(resume, "hh_resume_id", None) or getattr(resume, "hh_id", None)
    if not hh_resume_id:
        logger.warning("No HH resume id for %s", resume_id)
        return

    search_text = getattr(resume, "keywords", "") or ""
    try:
        items = await hh_client.search_similar_vacancies(text=search_text, resume_id=str(hh_resume_id), per_page=25)
    except Exception:
        logger.exception("HH search_similar_vacancies failed for resume_id=%s", resume_id)
        return

    found_ids = [str(i.get("id")).strip() for i in (items or []) if str(i.get("id") or "").strip()]
    if not found_ids:
        logger.info("No vacancies found for resume_id=%s", resume_id)
        return

    already = set(
        await ApplicationHistory.filter(
            resume_id=resume_id,
            vacancy_id__in=found_ids,
            status__in=[ApplicationStatus.SENT, ApplicationStatus.SUCCESS],
        ).values_list("vacancy_id", flat=True)
    )
    to_apply = [vid for vid in found_ids if vid not in already]
    if not to_apply:
        logger.info("All vacancies already applied. resume_id=%s", resume_id)
        return

    owner_id = getattr(resume, "user_id", None)
    queue = await _queue_for_user(owner_id) if owner_id is not None else QUEUE_NORMAL

    for vacancy_id in to_apply:
        apply_for_vacancy.apply_async(args=[resume_id, vacancy_id], queue=queue, routing_key=f"q.{queue}")

    logger.info(
        "Resume %s: found=%d, skipped=%d, enqueued=%d, queue=%s",
        resume_id, len(found_ids), len(already), len(to_apply), queue
    )


# ==========================
#   ОТКЛИК ПО ВАКАНСИИ
# ==========================

@shared_task(bind=True, name=f"{TASK_NS}.apply_for_vacancy")
def apply_for_vacancy(self, resume_id: int, vacancy_id: str) -> None:
    run_async(_apply_for_vacancy_async(resume_id, vacancy_id))


async def _apply_for_vacancy_async(resume_id: int, vacancy_id: str) -> None:
    await init_orm()

    # Получаем hh_resume_id для запроса к HH
    resume = await Resume.get_or_none(id=resume_id)
    if not resume:
        logger.warning("apply_for_vacancy: resume not found %s", resume_id)
        return

    hh_resume_id = getattr(resume, "hh_resume_id", None) or getattr(resume, "hh_id", None)
    if not hh_resume_id:
        logger.warning("apply_for_vacancy: no hh_resume_id for %s", resume_id)
        return

    try:
        hh_resume, vacancy = await asyncio.gather(
            hh_client.get_resume(str(hh_resume_id)),
            hh_client.get_vacancy(str(vacancy_id)),
        )
        cover_letter = await generate_cover_letter(hh_resume, vacancy)
        ok = await hh_client.apply_to_vacancy(resume_id=str(hh_resume_id), vacancy_id=str(vacancy_id), message=cover_letter)
    except Exception:
        logger.exception("apply_for_vacancy failed: resume_id=%s vacancy_id=%s", resume_id, vacancy_id)
        ok = False

    try:
        await ApplicationHistory.create(
            resume_id=resume_id,
            vacancy_id=str(vacancy_id),
            status=ApplicationStatus.SUCCESS if ok else ApplicationStatus.FAILED,
            provider_meta=None,
        )
    except Exception:
        logger.exception("ApplicationHistory create failed: resume_id=%s vacancy_id=%s", resume_id, vacancy_id)

    logger.debug("apply_for_vacancy done: resume_id=%s vacancy_id=%s ok=%s", resume_id, vacancy_id, ok)


# ==========================
#    ЛОКАЛЬНЫЙ ЗАПУСК
# ==========================
if __name__ == "__main__":
    argv = [
        "-A", "src.celery_app.celery_app",
        "worker",
        "-l", "INFO",
        "-Q", "high,normal,low,retry",
        "--concurrency=4",
    ]
    if os.name == "nt" or platform.system().lower().startswith("win"):
        argv += ["--pool=solo"]
    celery_app.start(argv)
