# src/models/application_result.py
from tortoise.models import Model
from tortoise import fields


class ApplicationResult(Model):
    """
    Статистика по обработке вакансий для конкретного пользователя/резюме.
    """
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="application_results", on_delete=fields.CASCADE)
    resume = fields.ForeignKeyField("models.Resume", related_name="application_results", on_delete=fields.CASCADE)

    total_vacancies = fields.IntField()           # всего найдено вакансий
    sent_applications = fields.IntField()         # успешно отправлено
    skipped_tests = fields.JSONField(default=list)  # список ID вакансий с тестами

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "application_results"
