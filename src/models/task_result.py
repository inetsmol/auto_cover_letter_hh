# src/models/task_result.py

from __future__ import annotations

from enum import Enum

from tortoise import fields, models


class RunType(str, Enum):
    FREE_DAILY = "free_daily"
    PAID_HOURLY = "paid_hourly"
    BULK = "bulk"
    MANUAL = "manual"


class TaskResult(models.Model):
    id: int = fields.IntField(pk=True)

    user = fields.ForeignKeyField(
        "models.User",
        related_name="task_results",
        on_delete=fields.OnDelete.CASCADE,
    )

    run_type: RunType = fields.CharEnumField(RunType, max_length=16)

    resumes_enqueued: int = fields.IntField(default=0)
    meta = fields.JSONField(null=True)

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "task_result"
        indexes = (
            ("user_id", "created_at"),
            ("run_type",),
        )

    def __str__(self) -> str:
        return f"{self.user.id}:{self.run_type}:{self.resumes_enqueued}"
