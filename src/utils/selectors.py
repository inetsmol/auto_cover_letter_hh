from __future__ import annotations

import asyncio
from typing import Iterable, List

from tortoise.expressions import Q
from tortoise.timezone import now

from src.db.init import init_db, close_db
from src.models import Subscription, Resume, User


async def get_active_user_ids_for_notification() -> List[int]:
    """
    Вернем список ИД активных пользователей с включенными уведомлениями
    """
    active_q = Q(user_status="active") & Q(notifications=True)
    ids = await User.filter(active_q).values_list("id", flat=True)
    return list(ids)


async def get_active_user_ids(plans: Iterable[str]) -> List[int]:
    """
    Вернёт user_id пользователей с активной подпиской из набора планов.
    Активная = status='active' и (expires_at IS NULL или expires_at > now()).
    """
    plans_list = list(plans)
    if not plans_list:
        return []

    active_q = Q(status="active") & (Q(expires_at=None) | Q(expires_at__gt=now()))
    ids = await Subscription.filter(active_q, plan__in=plans_list).values_list("user_id", flat=True)
    return list(ids)


async def get_active_resume_ids(user_id: int, status: str = "active") -> List[str]:
    """
    Вернёт список id резюме пользователя с нужным статусом (по умолчанию 'active').
    """
    ids = await Resume.filter(user_id=user_id, status=status).values_list("id", flat=True)
    return list(ids)


if __name__ == "__main__":
    import asyncio
    async def _test():
        await init_db()
        try:
            ids = await get_active_user_ids_for_notification()
            print(ids)
        finally:
            await close_db()
    asyncio.run(_test())
