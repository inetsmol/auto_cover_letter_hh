# src/models/hh_token.py
from __future__ import annotations

from datetime import timedelta
from typing import Optional, Dict, Any

from tortoise import fields
from tortoise.models import Model
from tortoise.timezone import now


class HHToken(Model):
    """
    Модель для хранения пользовательских OAuth-токенов HH (access/refresh).

    Архитектура:
    - Один пользователь Telegram -> один набор токенов HH (OneToOne).
    - Храним время истечения access-токена (UTC) для безопасного авто-рефреша.
    - Сырой ответ от /oauth/token опционально складываем в JSON для отладки/аудита.

    Лучшие практики:
    - Все datetime значения храним в UTC (Tortoise по умолчанию использует aware-дату при включенном use_tz).
    - Добавляем небольшой "скью" при проверке валидности, чтобы избежать гонок на границе истечения.
    """

    class Meta:
        table = "hh_tokens"
        # Индекс по updated_at пригодится для очистки/ротации старых записей
        indexes = ("updated_at",)

    # Связь 1:1 с вашим пользователем (TG user). related_name -> user.hh_token
    user: fields.OneToOneRelation["User"] = fields.OneToOneField(
        "models.User",
        related_name="hh_token",
        on_delete=fields.CASCADE,
    )

    # --- Токены ---
    access_token: str = fields.CharField(max_length=2048)
    refresh_token: str = fields.CharField(max_length=2048)
    token_type: str = fields.CharField(max_length=32, default="bearer")  # обычно "bearer"
    scope: Optional[str] = fields.CharField(max_length=512, null=True)   # если HH вернёт scope

    # --- Время жизни access-токена ---
    expires_at = fields.DatetimeField(null=True)  # UTC-aware; когда access-токен перестанет быть валидным

    # --- Служебные поля ---
    raw_payload = fields.JSONField(null=True)     # сырой ответ /oauth/token (для аудита/отладки)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    def is_access_valid(self, skew_seconds: int = 30) -> bool:
        """
        Проверить, что access-токен ещё валиден с заданным буфером времени.
        :param skew_seconds: буфер (сек), чтобы не попасть на край истечения.
        """
        if not self.expires_at:
            return False
        return now() + timedelta(seconds=skew_seconds) < self.expires_at

    async def update_from_token_response(
        self,
        payload: Dict[str, Any],
        *,
        save_raw: bool = True,
    ) -> None:
        """
        Обновить поля токенов из ответа HH /oauth/token.

        Ожидаемый payload (пример):
        {
            "access_token": "...",
            "token_type": "bearer",
            "expires_in": 1209599,
            "refresh_token": "..."
        }

        Примечание:
        - HH иногда может не прислать новый refresh_token при refresh-гранте — в этом случае
          оставляем старый.
        """
        # --- Безопасные извлечения значений ---
        acc = payload.get("access_token")
        if not acc:
            raise ValueError("В ответе отсутствует access_token")

        self.access_token = acc
        self.token_type = payload.get("token_type", self.token_type or "bearer")

        # Если передали новый refresh_token — обновим
        new_rt = payload.get("refresh_token")
        if new_rt:
            self.refresh_token = new_rt

        # Пересчёт времени истечения access-токена
        expires_in = int(payload.get("expires_in", 0)) or 0
        if expires_in > 0:
            self.expires_at = now() + timedelta(seconds=expires_in)
        else:
            # На всякий случай считаем, что токен истёк, чтобы заставить последующий refresh
            self.expires_at = None

        if save_raw:
            self.raw_payload = payload

        await self.save()
