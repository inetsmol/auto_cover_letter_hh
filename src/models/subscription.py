from enum import Enum
from typing import Optional

from tortoise import fields, models
from tortoise.timezone import now


class Plan(str, Enum):
    FREE = "free"
    PLUS = "plus"
    PRO = "pro"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELED = "canceled"


class Subscription(models.Model):
    id: int = fields.IntField(pk=True)

    # одна запись на пользователя — используем OneToOne
    user = fields.OneToOneField(
        "models.User",
        related_name="subscription",
        on_delete=fields.OnDelete.CASCADE,
    )

    plan: Plan = fields.CharEnumField(Plan, max_length=8, default=Plan.FREE)
    status: SubscriptionStatus = fields.CharEnumField(
        SubscriptionStatus, max_length=10, default=SubscriptionStatus.ACTIVE
    )

    started_at = fields.DatetimeField(auto_now_add=True)
    # для платных планов может быть срок действия
    expires_at: Optional[fields.DatetimeField] = fields.DatetimeField(null=True)
    # если пользователь отменил (даже до истечения)
    canceled_at: Optional[fields.DatetimeField] = fields.DatetimeField(null=True)

    # под будущие интеграции (Telegram Stars и пр.)
    payment_meta = fields.JSONField(null=True)

    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "subscription"
        indexes = (("plan",), ("status",), ("expires_at",))

    def __str__(self) -> str:
        return f"{self.user.id}:{self.plan}/{self.status}"

    @property
    def is_active(self) -> bool:
        """Удобная проверка активности подписки."""
        if self.status != SubscriptionStatus.ACTIVE:
            return False
        if self.expires_at:
            return self.expires_at > now()
        return True
