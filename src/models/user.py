from tortoise.models import Model
from tortoise import fields


class User(Model):
    table = "users"

    USER_STATUS_CHOICES = [
        ('active', 'Active'),
        ('blocked', 'Blocked'),
    ]
    # Данные из ТГ
    id = fields.BigIntField(pk=True)
    username = fields.CharField(max_length=100, null=True)
    first_name = fields.CharField(max_length=100, null=True)
    last_name = fields.CharField(max_length=100, null=True)

    vacancy_id = fields.CharField(max_length=100, null=True)
    text_for_filter = fields.TextField(null=True)
    notifications = fields.BooleanField(default=False)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    user_status = fields.CharField(max_length=10, choices=USER_STATUS_CHOICES, default='active')
