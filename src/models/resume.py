# src/models/resume.py
from tortoise.models import Model
from tortoise import fields


class Resume(Model):
    class Meta:
        table = "resumes"

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    id = fields.CharField(pk=True, max_length=40)
    user = fields.ForeignKeyField(
        "models.User",
        related_name="resumes",  # соответствует User.resumes
        on_delete=fields.CASCADE
    )
    positive_keywords = fields.JSONField(null=True)
    negative_keywords = fields.JSONField(null=True)
    resume_json = fields.JSONField(null=True)
    status = fields.CharField(max_length=10, choices=STATUS_CHOICES, default='inactive')

    @property
    def keywords(self):
        if not self.positive_keywords:
            return ""  # Без ключевых слов поиск невозможен
        search = " OR ".join(self.positive_keywords)
        if self.negative_keywords:
            search += " " + " ".join(f"NOT {w}" for w in self.negative_keywords)
        return search
