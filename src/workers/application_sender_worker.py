# src/workers/application_sender_worker.py
from __future__ import annotations

import asyncio
import logging
import os
import platform
from typing import Any, Iterable, Optional

from celery import shared_task
from tortoise import Tortoise
from tortoise.expressions import Q
from tortoise.timezone import now

from src.celery_app import celery_app
from src.db.config import TORTOISE_ORM
from src.models import (
    User,
    Resume,
    Subscription,
    Plan,
    SubscriptionStatus,
    ApplicationHistory,
    ApplicationStatus,
)

from src.services.task_manager.result_processor import save_run_result
from src.services.notification.telegram_notifier import send_processing_summary

logger = logging.getLogger(__name__)

# Очереди
QUEUE_HIGH = "high"
QUEUE_NORMAL = "normal"
QUEUE_LOW = "low"
QUEUE_RETRY = "retry"

TASK_NS = "workers.application_sender"

_ORM_READY = False


async def init_orm() -> None:
    global _ORM_READY
    if _ORM_READY:
        return
    await Tortoise.init(config=TORTOISE_ORM)
    _ORM_READY = True
    logger.info("Tortoise ORM initialized in worker process.")


def run_async(coro):
    async def _runner():
        await init_orm()
        return await coro
    return asyncio.run(_runner())


# ==========================================================
#                  ВЕРХНЕУРОВНЕВЫЕ ПЛАНИРОВЩИКИ
# ==========================================================

@shared_task(
    bind=True,
    name=f"{TASK_NS}.schedule_bulk_apply",
)
def schedule_bulk_apply(self, user_id: Optional[int] = None) -> dict[str, Any]:
    """
    Универсальный планировщик.
    Для каждого пользователя сохраняет результат пробега и отправляет уведомление.
    """
    # run_type — метка запуска, чтобы различать ручной/массовый
    run_type = "manual" if user_id else "bulk"
    return run_async(_schedule_bulk_apply_and_persist_async(user_id=user_id, run_type=run_type))


async def _schedule_bulk_apply_and_persist_async(
    *,
    user_id: Optional[int],
    run_type: str,
    force_queue: Optional[str] = None,
) -> dict[str, Any]:
    await init_orm()

    if user_id is not None:
        user_ids: list[int] = [user_id]
    else:
        active_q = Q(status=SubscriptionStatus.ACTIVE) & (Q(expires_at=None) | Q(expires_at__gt=now()))
        user_ids = list(await Subscription.filter(active_q).values_list("user_id", flat=True))

    total_users = 0
    total_resumes_enqueued = 0
    per_user_stats: list[dict] = []

    for uid in user_ids:
        stats = await _schedule_bulk_apply_async(user_id=uid, force_queue=force_queue)
        total_users += 1
        total_resumes_enqueued += int(stats.get("resumes_enqueued", 0))
        per_user_stats.append({"user_id": uid, **stats})

        # Сохраняем результат пробега и уведомляем
        try:
            tr = await save_run_result(
                user_id=uid,
                run_type=run_type,
                resumes_enqueued=stats.get("resumes_enqueued", 0),
                meta={
                    "queue": stats.get("force_queue"),
                    "users_processed": stats.get("users_processed"),
                },
            )
            await send_processing_summary(
                user_id=uid,
                run_type=run_type,
                resumes_enqueued=stats.get("resumes_enqueued", 0),
            )
        except Exception as e:
            logger.exception("Persist/notify failed for user %s: %s", uid, e)

    summary = {
        "users_processed": total_users,
        "resumes_enqueued_total": total_resumes_enqueued,
        "run_type": run_type,
    }
    logger.info("schedule_bulk_apply summary: %s", summary)
    return summary


async def _schedule_bulk_apply_async(user_id: Optional[int] = None,
                                     force_queue: Optional[str] = None) -> dict[str, Any]:
    """
    Выбираем резюме и ставим подзадачи apply_for_resume.
    Если force_queue передана — используем её, иначе выбираем исходя из подписки владельца.
    """
    await init_orm()

    if user_id is None:
        return {"users_processed": 0, "resumes_enqueued": 0, "reason": "user_id_required_for_internal_call"}

    # рассчитать очередь для подзадач
    queue = force_queue or await _queue_for_user(user_id)

    resumes = list(await Resume.filter(user_id=user_id, is_active=True).values_list("id", flat=True))

    resumes_enqueued = 0
    for rid in resumes:
        apply_for_resume.apply_async(
            args=[rid],
            queue=queue,
            routing_key=f"q.{queue}",
        )
        resumes_enqueued += 1

    result = {
        "users_processed": 1,
        "resumes_enqueued": resumes_enqueued,
        "force_queue": force_queue,
    }
    logger.info("schedule_bulk_apply (user=%s): %s", user_id, result)
    return result


async def _queue_for_user(user_id: int) -> str:
    sub = await Subscription.get_or_none(user_id=user_id)
    if not sub:
        return QUEUE_NORMAL
    if sub.status != SubscriptionStatus.ACTIVE:
        return QUEUE_LOW
    if sub.plan == Plan.FREE:
        return QUEUE_LOW
    if sub.plan in (Plan.PLUS, Plan.PRO):
        return QUEUE_HIGH
    return QUEUE_NORMAL


# -------------------------------
#   КОГОРТНЫЕ ПЛАНИРОВЩИКИ
# -------------------------------

@shared_task(
    bind=True,
    name=f"{TASK_NS}.schedule_free_daily",
    queue=QUEUE_LOW,  # минимальный приоритет для запуска
)
def schedule_free_daily(self) -> dict[str, Any]:
    """
    FREE-когорта: 1 раз в день 12:00 MSK (см. celery_beat.py).
    Дочерние задачи ставятся в low, для каждого пользователя сохраняем результат и шлём нотификацию.
    """
    return run_async(_schedule_for_cohort_and_persist_async(plans=[Plan.FREE], child_queue=QUEUE_LOW, run_type="free_daily"))


@shared_task(
    bind=True,
    name=f"{TASK_NS}.schedule_paid_hourly",
    queue=QUEUE_HIGH,
)
def schedule_paid_hourly(self) -> dict[str, Any]:
    """
    PLUS/PRO: каждый час (00 минут). Дочерние — в high, с сохранением результата и нотификацией.
    """
    return run_async(_schedule_for_cohort_and_persist_async(plans=[Plan.PLUS, Plan.PRO], child_queue=QUEUE_HIGH, run_type="paid_hourly"))


async def _schedule_for_cohort_and_persist_async(
    *,
    plans: Iterable[Plan],
    child_queue: str,
    run_type: str,
) -> dict[str, Any]:
    await init_orm()

    active_q = Q(status=SubscriptionStatus.ACTIVE) & (Q(expires_at=None) | Q(expires_at__gt=now()))
    user_ids = list(await Subscription.filter(active_q, plan__in=list(plans)).values_list("user_id", flat=True))

    enqueued = 0
    for uid in user_ids:
        stats = await _schedule_bulk_apply_async(user_id=uid, force_queue=child_queue)
        enqueued += int(stats.get("resumes_enqueued", 0))

        # Персист и нотификация — для каждого пользователя
        try:
            await save_run_result(
                user_id=uid,
                run_type=run_type,
                resumes_enqueued=stats.get("resumes_enqueued", 0),
                meta={"queue": child_queue},
            )
            await send_processing_summary(
                user_id=uid,
                run_type=run_type,
                resumes_enqueued=stats.get("resumes_enqueued", 0),
            )
        except Exception as e:
            logger.exception("Persist/notify failed for user %s: %s", uid, e)

    result = {
        "plans": [p.value for p in plans],
        "users": len(user_ids),
        "resumes_enqueued_total": enqueued,
        "child_queue": child_queue,
        "run_type": run_type,
    }
    logger.info("schedule_for_cohort: %s", result)
    return result


# ==========================================================
#                РЕЗЮМЕ → ПОИСК → ВАКАНСИИ
# ==========================================================

@shared_task(
    bind=True,
    name=f"{TASK_NS}.apply_for_resume",
)
def apply_for_resume(self, resume_id: int) -> dict[str, Any]:
    return run_async(_apply_for_resume_async(resume_id))


async def _apply_for_resume_async(resume_id: int) -> dict[str, Any]:
    """
    1) Ищем похожие вакансии через HH client
    2) Отбрасываем те, где уже есть SENT/SUCCESS
    3) Ставим apply_for_vacancy(...)
    """
    await init_orm()

    # Импорты локально, чтобы не тянуть их при импорте модуля
    from src.services.hh_client import hh_client  # твой клиент
    # Модели уже импортированы сверху

    resume: Resume | None = await Resume.get_or_none(id=resume_id)
    if not resume:
        return {"resume_id": resume_id, "vacancies_found": 0, "vacancies_enqueued": 0, "reason": "resume_not_found"}

    if hasattr(resume, "is_active") and not bool(getattr(resume, "is_active")):
        return {"resume_id": resume_id, "vacancies_found": 0, "vacancies_enqueued": 0, "reason": "resume_inactive"}

    hh_resume_id = getattr(resume, "hh_resume_id", None) or getattr(resume, "hh_id", None)
    if not hh_resume_id:
        return {"resume_id": resume_id, "vacancies_found": 0, "vacancies_enqueued": 0, "reason": "no_hh_resume_id"}

    # Текст для поиска
    search_text = resume.keywords

    try:
        items = await hh_client.search_similar_vacancies(
            text=search_text,
            resume_id=str(hh_resume_id),
            per_page=25,
        )
    except Exception as e:
        logger.exception("HH search_similar_vacancies failed for resume %s: %s", resume_id, e)
        return {"resume_id": resume_id, "vacancies_found": 0, "vacancies_enqueued": 0, "reason": "hh_search_failed"}

    found_ids: list[str] = []
    for it in (items or []):
        vid = str(it.get("id") or "").strip()
        if vid:
            found_ids.append(vid)

    if not found_ids:
        return {"resume_id": resume_id, "vacancies_found": 0, "vacancies_enqueued": 0, "reason": "no_vacancies"}

    # Только те, куда ещё не откликались (SENT/SUCCESS считаем попыткой)
    already = set(
        await ApplicationHistory.filter(
            resume_id=resume_id,
            vacancy_id__in=found_ids,
            status__in=[ApplicationStatus.SENT, ApplicationStatus.SUCCESS],
        ).values_list("vacancy_id", flat=True)
    )
    to_apply = [vid for vid in found_ids if vid not in already]

    if not to_apply:
        return {
            "resume_id": resume_id,
            "vacancies_found": len(found_ids),
            "vacancies_enqueued": 0,
            "already_applied_skipped": len(already),
            "reason": "all_already_applied",
        }

    owner_id = getattr(resume, "user_id", None)
    queue_for_child = await _queue_for_user(owner_id) if owner_id is not None else QUEUE_NORMAL

    enqueued = 0
    for vacancy_id in to_apply:
        apply_for_vacancy.apply_async(
            args=[resume_id, vacancy_id],
            queue=queue_for_child,
            routing_key=f"q.{queue_for_child}",
        )
        enqueued += 1

    result = {
        "resume_id": resume_id,
        "vacancies_found": len(found_ids),
        "already_applied_skipped": len(already),
        "vacancies_enqueued": enqueued,
        "queue": queue_for_child,
        "sample_vacancy_ids": to_apply[:5],
    }
    logger.info("apply_for_resume: %s", result)
    return result


# ==========================================================
#              АТОМАРНЫЙ ОТКЛИК ПО ВАКАНСИИ
# ==========================================================

@shared_task(
    bind=True,
    name=f"{TASK_NS}.apply_for_vacancy",
)
def apply_for_vacancy(self, resume_id: int, vacancy_id: str) -> dict[str, Any]:
    return run_async(_apply_for_vacancy_async(resume_id, vacancy_id))


async def _apply_for_vacancy_async(resume_id: int, vacancy_id: str) -> dict[str, Any]:
    await init_orm()

    # TODO: интегрировать генерацию письма и вызов HH API
    # Здесь же можно создавать ApplicationHistory.(mark_success/mark_failed) после ответа HH.
    ok = True
    provider_meta = None

    result = {"resume_id": resume_id, "vacancy_id": vacancy_id, "ok": bool(ok), "provider_meta": provider_meta}
    logger.debug("apply_for_vacancy: %s", result)
    return result


# ==========================================================
#                    ЛОКАЛЬНЫЙ ЗАПУСК ВОРКЕРА
# ==========================================================
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
