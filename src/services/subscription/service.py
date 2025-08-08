# src/services/subscription/service.py

from src.models import Subscription, SubscriptionStatus, Plan, User

async def ensure_subscription_for_user(user: User) -> Subscription:
    """
    Создаёт подписку FREE/ACTIVE, если у пользователя ещё нет подписки.
    Возвращает существующую/созданную подписку.
    """
    sub, _ = await Subscription.get_or_create(
        user=user,
        defaults={
            "plan": Plan.FREE,
            "status": SubscriptionStatus.ACTIVE,
            "expires_at": None,
            "canceled_at": None,
        },
    )
    return sub
