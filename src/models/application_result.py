# src/models/application_result.py

from tortoise.models import Model
from tortoise import fields, timezone


class ApplicationResult(Model):
    """
    Статистика по обработке вакансий для конкретного пользователя/резюме.
    """

    # == Идентификаторы ==
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField(
        "models.User",
        related_name="application_results",
        on_delete=fields.CASCADE,
    )
    resume = fields.ForeignKeyField(
        "models.Resume",
        related_name="application_results",
        on_delete=fields.CASCADE,
    )

    # == Метрики ==
    total_vacancies = fields.IntField()                 # всего найдено вакансий
    sent_applications = fields.IntField()               # успешно отправлено
    skipped_tests = fields.JSONField(default=list)      # список ID вакансий с тестами

    # == Уведомление пользователя ==
    notified = fields.BooleanField(default=False)       # флаг: уведомление отправлено
    notified_at = fields.DatetimeField(null=True)       # когда отправлено (UTC)

    # == Служебные поля ==
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "application_results"
        # Индексы для частых выборок (например, «найти неуведомлённые»)
        indexes = (
            ("notified",),                        # быстрый фильтр по флагу
            ("user", "resume", "created_at"),     # частая аналитика по пользователю/резюме
        )


# --- Удобный helper для безопасной пометки как уведомлённого ---
async def mark_notified(self) -> None:
    """
    Пометить запись как уведомлённую.
    Идемпотентно: повторные вызовы просто обновят время, если нужно.
    """
    self.notified = True
    self.notified_at = timezone.now()
    # Обновляем только изменённые поля — быстрее и чище
    await self.save(update_fields=("notified", "notified_at"))