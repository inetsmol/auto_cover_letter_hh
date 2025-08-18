# src/workers/apply.py

import asyncio
from typing import List, Optional

from tortoise.expressions import Q
from tortoise.timezone import now

from src.celery_app import celery_app
from src.db.init import init_db, close_db
from src.models import Resume, Subscription
from src.tasks.apply import apply_for_resume_task

# === NEW: инициализация пула OpenAI на процесс воркера ===
from celery.signals import worker_process_init, worker_process_shutdown
from src.services.ai.openai_pool import setup as ai_setup, teardown as ai_teardown, OpenAISettings
from src.config import config

@worker_process_init.connect
def _on_worker_proc_init(**_: dict) -> None:
    """Поднимаем фоновый цикл и инициализируем httpx/AsyncOpenAI один раз на процесс."""
    settings = OpenAISettings(
        api_key=config.ai.openai_api_key.get_secret_value(),
        proxy_url=(config.ai.proxy_url or None),
        connect_timeout=15.0,
        read_timeout=60.0,
        pool_timeout=60.0,
        http2=True,
    )
    ai_setup(settings)


@worker_process_shutdown.connect
def _on_worker_proc_shutdown(**_: dict) -> None:
    """Аккуратно закрываем клиентов и останавливаем фон.цикл на завершении процесса."""
    ai_teardown()
# === END NEW ===


async def _active_user_ids(plans: List[str]) -> List[int]:
    # Активная подписка и не истекла
    active_q = Q(status="active") & (Q(expires_at=None) | Q(expires_at__gt=now()))
    ids = await Subscription.filter(active_q, plan__in=plans).values_list("user_id", flat=True)
    return list(ids)


async def _active_resume_ids(user_id: int) -> List[str]:
    return list(
        await Resume.filter(user_id=user_id, status="active").values_list("id", flat=True)
    )


async def _process_resume(resume_id: str, cap: Optional[int] = None) -> int:
    """
    Возвращает число успешно отправленных откликов для данного резюме.
    """
    return await apply_for_resume_task(resume_id, cap)


@celery_app.task(name="src.workers.apply.run_paid_hourly")
def run_paid_hourly():
    """
    Каждые час — обрабатываем все активные резюме у платных (plus/pro).
    """
    async def _run():
        await init_db()
        try:
            user_ids = await _active_user_ids(["plus", "pro"])
            for uid in user_ids:
                remaining = 3
                if remaining <= 0:
                    continue
                for rid in await _active_resume_ids(uid):
                    if remaining <= 0:
                        break
                    sent = await _process_resume(resume_id=rid, cap=remaining)
                    remaining -= sent
        finally:
            await close_db()

    asyncio.run(_run())


@celery_app.task(name="src.workers.apply.run_free_daily")
def run_free_daily():
    """
    Раз в день (12:00 МСК) — для free максимум 3 отклика на пользователя.
    Лимит распределяется по резюме пользователя последовательно.
    """
    async def _run():
        await init_db()
        try:
            user_ids = await _active_user_ids(["free"])
            for uid in user_ids:
                remaining = 3
                if remaining <= 0:
                    continue
                for rid in await _active_resume_ids(uid):
                    if remaining <= 0:
                        break
                    sent = await _process_resume(resume_id=rid, cap=remaining)
                    remaining -= sent
        finally:
            await close_db()

    asyncio.run(_run())




# import asyncio
# from typing import List, Optional
#
# from tortoise.expressions import Q
# from tortoise.timezone import now
#
# from src.celery_app import celery_app
# from src.db.init import init_db, close_db
# from src.models import Resume, Subscription
# from src.tasks.apply import apply_for_resume_task
#
# _DB_READY = False
#
#
# async def _active_user_ids(plans: List[str]) -> List[int]:
#     # Активная подписка и не истекла
#     active_q = Q(status="active") & (Q(expires_at=None) | Q(expires_at__gt=now()))
#     ids = await Subscription.filter(active_q, plan__in=plans).values_list("user_id", flat=True)
#     return list(ids)
#
#
# async def _active_resume_ids(user_id: int) -> List[str]:
#     return list(
#         await Resume.filter(user_id=user_id, status="active").values_list("id", flat=True)
#     )
#
#
# async def _process_resume(resume_id: str, cap: Optional[int] = None) -> int:
#     """
#     Возвращает число успешно отправленных откликов для данного резюме.
#     """
#     return await apply_for_resume_task(resume_id, cap)
#
#
# @celery_app.task(name="src.workers.apply.run_paid_hourly")
# def run_paid_hourly():
#     """
#     Каждые час — обрабатываем все активные резюме у платных (plus/pro).
#     """
#     async def _run():
#         await init_db()
#         try:
#             user_ids = await _active_user_ids(["plus", "pro"])
#             for uid in user_ids:
#                 remaining = 10
#                 if remaining <= 0:
#                     continue
#                 for rid in await _active_resume_ids(uid):
#                     if remaining <= 0:
#                         break
#                     sent = await _process_resume(resume_id=rid, cap=remaining)
#                     remaining -= sent
#         finally:
#             await close_db()
#
#     asyncio.run(_run())
#
#
# @celery_app.task(name="src.workers.apply.run_free_daily")
# def run_free_daily():
#     """
#     Раз в день (12:00 МСК) — для free максимум 3 отклика на пользователя.
#     Лимит распределяется по резюме пользователя последовательно.
#     """
#     async def _run():
#         await init_db()
#         try:
#             user_ids = await _active_user_ids(["free"])
#             for uid in user_ids:
#                 remaining = 3
#                 if remaining <= 0:
#                     continue
#                 for rid in await _active_resume_ids(uid):
#                     if remaining <= 0:
#                         break
#                     sent = await _process_resume(resume_id=rid, cap=remaining)
#                     remaining -= sent
#         finally:
#             await close_db()
#
#     asyncio.run(_run())
