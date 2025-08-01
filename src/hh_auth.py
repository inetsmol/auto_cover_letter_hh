# src/hh_auth.py
import asyncio
import webbrowser
import datetime
from datetime import timedelta

import httpx

from src.bot_init import redis, bot
from src.config import config
from src.models import HHToken


async def get_access_token(timeout=60):
    # 1. Пробуем достать токен из редиса
    access_token = await redis.get(config.redis.access_token_key)
    if access_token:
        return access_token.decode()

    tokens = await HHToken.get_or_none(id=1)
    if not tokens:
        print("Отправляем ссылку админу в ТГ")
        await bot.send_message(
            config.bot.admin_id,
            f"Требуется авторизация в hh.ru\nПожалуйста, перейдите по ссылке: {config.hh.auth_url}"
        )
        # webbrowser.open(config.hh.auth_url)
        # Ожидание токена в Redis (polling)
        waited = 0
        while waited < timeout:
            await asyncio.sleep(1)
            waited += 1
            access_token = await redis.get(config.redis.access_token_key)
            if access_token:
                return access_token.decode()
        raise Exception("Авторизация не завершена: токен не получен за отведённое время")

    if tokens.access_token and tokens.expires_at and tokens.expires_at > datetime.datetime.now(datetime.UTC):
        # Кладём в Redis с TTL
        ttl = int((tokens.expires_at - datetime.datetime.now(datetime.UTC)).total_seconds())
        await redis.set(config.redis.access_token_key, tokens.access_token, ex=ttl)
        return access_token

    new_tokens = await refresh_tokens(tokens.refresh_token)

    return new_tokens["access_token"]


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
        expires_at = datetime.datetime.now(datetime.UTC) + timedelta(seconds=expires_in)

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


async def get_headers():
    access_token = await get_access_token()
    return {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "HH-Job-Bot (CodeGPT)"
    }
