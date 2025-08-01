from tortoise import fields, Model


class HHToken(Model):
    id = fields.IntField(pk=True)
    access_token = fields.CharField(max_length=512)
    refresh_token = fields.CharField(max_length=512)
    expires_at = fields.DatetimeField()
    updated_at = fields.DatetimeField(auto_now=True)
