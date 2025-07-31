# src/models/vacancy.py
from tortoise.models import Model
from tortoise import fields


class Vacancy(Model):
    class Meta:
        table = "vacancies"

    id = fields.CharField(pk=True, max_length=40)
    user = fields.ForeignKeyField(
        "models.User",
        related_name="vacancies",  # соответствует User.vacancies
        on_delete=fields.CASCADE
    )
    positive_keywords = fields.JSONField(null=True)
    negative_keywords = fields.JSONField(null=True)
    resume_json = fields.JSONField(null=True)

    @property
    def keywords(self):
        result = []
        result.extend(self.positive_keywords or [])
        result.extend(f"NOT {word}" for word in (self.negative_keywords or []))
        return " ".join(result)
