# src/services/auth/token_store.py
"""
Кастомный TokenStore для хранения токенов HH в БД через Tortoise ORM.
Поддерживает multi-tenant сценарий (один токен на пользователя).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from hh_api.auth import KeyedTokenStore, TokenPair
from hh_api.auth.utils import parse_dt_aware, to_dt_aware

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

    async def set_tokens(self, subject: int, tokens: TokenPair) -> None:
        """
        Сохранить токены для пользователя.

        Args:
            subject: user_id пользователя
            tokens: TokenPair с новыми токенами
        """
        try:
            # Подготавливаем данные для сохранения
            data = {
                "access_token": tokens.access_token or "",
                "refresh_token": tokens.refresh_token or "",
            }

            # Обрабатываем expires_at
            if tokens.expires_at:
                data["expires_at"] = to_dt_aware(tokens.expires_at)
            elif tokens.expires_in:
                # Вычисляем expires_at из expires_in
                data["expires_at"] = datetime.now(timezone.utc).replace(microsecond=0) + \
                                     timedelta(seconds=tokens.expires_in)
            else:
                data["expires_at"] = None

            # Обновляем или создаем запись
            token_record = await HHToken.get_or_none(user_id=subject)

            if token_record:
                # Обновляем существующую запись
                for key, value in data.items():
                    setattr(token_record, key, value)
                await token_record.save()
            elif self.auto_create:
                # Создаем новую запись
                await HHToken.create(
                    user_id=subject,
                    **data
                )
            else:
                raise ValueError(f"No token record for user {subject} and auto_create=False")

        except Exception as e:
            import logging
            logging.error(f"Error saving tokens for user {subject}: {e}")
            raise


class SingleTenantTortoiseStore:
    """
    Адаптер для single-tenant сценария (backward compatibility).
    Использует фиксированный user_id=1 для единого набора токенов.
    """

    def __init__(self, user_id: int = 1):
        self.user_id = user_id
        self.keyed_store = TortoiseTokenStore()

    async def get_tokens(self) -> Optional[TokenPair]:
        return await self.keyed_store.get_tokens(self.user_id)

    async def set_tokens(self, tokens: TokenPair) -> None:
        await self.keyed_store.set_tokens(self.user_id, tokens)


# Дополнительный helper для миграции старых токенов
async def migrate_legacy_tokens():
    """
    Мигрирует токены из старого формата (id=1) в новый (user_id based).
    """
    try:
        # Проверяем есть ли старая запись с id=1
        old_token = await HHToken.get_or_none(id=1)
        if old_token and not hasattr(old_token, 'user_id'):
            import logging
            logging.info("Found legacy token record, migration needed")
            # Здесь можно добавить логику миграции если нужно
    except Exception as e:
        import logging
        logging.warning(f"Token migration check failed: {e}")