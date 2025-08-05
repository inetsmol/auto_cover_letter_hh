import asyncio
import datetime

from src.auth.refresh_token import refresh_tokens
from src.bot_init import bot
from src.config import config
from src.models import HHToken
from src.redis_init import redis


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