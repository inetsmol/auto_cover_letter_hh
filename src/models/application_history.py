from __future__ import annotations

from enum import Enum
from typing import Optional

from tortoise import fields, models
from tortoise.timezone import now


class ApplicationStatus(str, Enum):
    """Состояние попытки отклика."""
    SENT = "sent"          # запрос к HH успешно отправлен
    SUCCESS = "success"    # HH принял отклик
    FAILED = "failed"      # ошибка при отправке/валидации
    SKIPPED = "skipped"    # пропущено (дубликат/фильтр/лимит и т.п.)


class ApplicationHistory(models.Model):
    """
    История откликов по вакансиям для конкретного резюме.
    Гарантия уникальности: одна запись на (resume_id, vacancy_id).
    """
    id: int = fields.IntField(pk=True)

    user = fields.ForeignKeyField(
        "models.User",
        related_name="applications",
        on_delete=fields.OnDelete.CASCADE,
    )
    resume = fields.ForeignKeyField(
        "models.Resume",
        related_name="applications",
        on_delete=fields.OnDelete.CASCADE,
    )

    # В HH id вакансии — строка; храним как строку
    vacancy_id: str = fields.CharField(max_length=32)

    status: ApplicationStatus = fields.CharEnumField(
        ApplicationStatus, max_length=8, default=ApplicationStatus.SENT
    )

    # Снапшоты и метаданные
    cover_letter: Optional[str] = fields.TextField(null=True)      # что отправили
    provider_meta = fields.JSONField(null=True)                    # сырые данные/ответ HH
    error: Optional[str] = fields.TextField(null=True)             # текст ошибки при FAILED

    # Временные метки
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    applied_at = fields.DatetimeField(null=True)                   # когда HH принял (для SUCCESS)

    class Meta:
        table = "application_history"
        unique_together = (("resume", "vacancy_id"),)
        indexes = (
            ("user_id", "created_at"),
            ("resume_id", "created_at"),
            ("vacancy_id",),
            ("status",),
        )

    def __str__(self) -> str:
        return f"{self.resume.id}:{self.vacancy_id}:{self.status}"

    @classmethod
    async def mark_success(
        cls,
        *,
        user_id: int,
        resume_id: int,
        vacancy_id: str,
        cover_letter: Optional[str] = None,
        provider_meta: Optional[dict] = None,
    ) -> "ApplicationHistory":
        obj, _ = await cls.get_or_create(
            resume_id=resume_id,
            vacancy_id=vacancy_id,
            defaults={
                "user_id": user_id,
                "status": ApplicationStatus.SUCCESS,
                "cover_letter": cover_letter,
                "provider_meta": provider_meta,
                "applied_at": now(),
            },
        )
        # если запись существовала, обновим статус и поля
        obj.user_id = user_id
        obj.status = ApplicationStatus.SUCCESS
        obj.cover_letter = cover_letter
        obj.provider_meta = provider_meta
        obj.applied_at = now()
        await obj.save(update_fields=["user_id", "status", "cover_letter", "provider_meta", "applied_at", "updated_at"])
        return obj

    @classmethod
    async def mark_failed(
        cls,
        *,
        user_id: int,
        resume_id: int,
        vacancy_id: str,
        error: str,
        provider_meta: Optional[dict] = None,
    ) -> "ApplicationHistory":
        obj, _ = await cls.get_or_create(
            resume_id=resume_id,
            vacancy_id=vacancy_id,
            defaults={
                "user_id": user_id,
                "status": ApplicationStatus.FAILED,
                "error": error,
                "provider_meta": provider_meta,
            },
        )
        obj.user_id = user_id
        obj.status = ApplicationStatus.FAILED
        obj.error = error
        obj.provider_meta = provider_meta
        await obj.save(update_fields=["user_id", "status", "error", "provider_meta", "updated_at"])
        return obj

    @classmethod
    async def mark_skipped(
        cls,
        *,
        user_id: int,
        resume_id: int,
        vacancy_id: str,
        reason: str = "duplicate",
    ) -> "ApplicationHistory":
        obj, _ = await cls.get_or_create(
            resume_id=resume_id,
            vacancy_id=vacancy_id,
            defaults={
                "user_id": user_id,
                "status": ApplicationStatus.SKIPPED,
                "error": reason,
            },
        )
        obj.user_id = user_id
        obj.status = ApplicationStatus.SKIPPED
        obj.error = reason
        await obj.save(update_fields=["user_id", "status", "error", "updated_at"])
        return obj
