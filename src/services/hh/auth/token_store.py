# src/services/auth/token_store.py
"""
Кастомный TokenStore для хранения токенов HH в БД через Tortoise ORM.
Поддерживает multi-tenant сценарий (один токен на пользователя).
"""
from __future__ import annotations

from typing import Optional

from hh_api.auth import KeyedTokenStore, TokenPair
from hh_api.auth.utils import to_dt_aware

from src.models import HHToken


class TortoiseTokenStore(KeyedTokenStore[int]):
    """
    Хранилище токенов в БД через Tortoise ORM.
    Использует модель HHToken с user_id как ключом.
    """

    def __init__(self, *, auto_create: bool = True):
        """
        Args:
            auto_create: Автоматически создавать запись если её нет
        """
        self.auto_create = auto_create

    async def get_tokens(self, subject: int) -> Optional[TokenPair]:
        """
        Получить токены для пользователя.

        Args:
            subject: user_id пользователя

        Returns:
            TokenPair или None если токенов нет
        """
        try:
            # Ищем токен по user_id
            token_record = await HHToken.get_or_none(user_id=subject)

            if not token_record:
                return None

            # Проверяем наличие хотя бы одного токена
            if not token_record.access_token and not token_record.refresh_token:
                return None

            # Конвертируем expires_at в aware datetime если нужно
            expires_at = None
            if token_record.expires_at:
                expires_at = to_dt_aware(token_record.expires_at)

            return TokenPair(
                access_token=token_record.access_token,
                refresh_token=token_record.refresh_token,
                expires_in=None,  # вычисляется из expires_at если нужно
                expires_at=expires_at
            )

        except Exception as e:
            # Логируем ошибку но не падаем
            import logging
            logging.error(f"Error getting tokens for user {subject}: {e}")
            return None

    async def set_tokens(self, subject: int, new_tokens: TokenPair) -> None:
        """
        Сохранить токены для пользователя.

        Args:
            subject: user_id пользователя
            new_tokens: TokenPair с новыми токенами
        """
        try:

            tokens, created = await HHToken.get_or_create(
                user_id=subject,
                defaults={
                    "access_token": new_tokens.access_token or "",
                    "refresh_token": new_tokens.refresh_token or "",
                    "expires_at": new_tokens.expires_at or ""
                }
            )
            if not created:
                to_update = []
                new_access_token = new_tokens.access_token or ""
                new_refresh_token = new_tokens.refresh_token or ""
                new_expires_at = new_tokens.expires_at or ""

                if tokens.access_token != new_access_token:
                    tokens.access_token = new_access_token
                    to_update.append("access_token")
                if tokens.refresh_token != new_refresh_token:
                    tokens.refresh_token = new_refresh_token
                    to_update.append("refresh_token")
                if tokens.expires_at != new_expires_at:
                    tokens.expires_at = new_expires_at
                    to_update.append("expires_at")

                if to_update:
                    await tokens.save(update_fields=to_update)

        except Exception as e:
            import logging
            logging.error(f"Error saving tokens for user {subject}: {e}")
            raise
