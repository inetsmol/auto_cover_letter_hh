import datetime

import httpx

from src.config import config
from src.models import HHToken
from src.redis_init import redis


async def refresh_tokens(refresh_token: str):
    """Обновление токенов"""

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": config.hh.client_id.get_secret_value(),
        "client_secret": config.hh.client_secret.get_secret_value(),
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(config.hh.token_url, data=data)
        if response.status_code != 200:
            raise Exception(f"Не удалось обновить токены: {response.text}")

        tokens = response.json()
        access_token = tokens.get("access_token")
        new_refresh_token = tokens.get("refresh_token", refresh_token)  # На всякий случай, если hh.ru вернёт новый refresh_token
        expires_in = tokens.get("expires_in", 3600)
        expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=expires_in)

        # Сохраняем в базу
        tokens = await HHToken.get(id=1)
        tokens.access_token = access_token
        tokens.refresh_token = new_refresh_token
        tokens.access_expires_at = expires_at
        await tokens.save()

        # Сохраняем в Redis, если передан клиент
        if redis:
            await redis.set(config.redis.access_token_key, access_token, ex=expires_in)

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "expires_in": expires_in
        }