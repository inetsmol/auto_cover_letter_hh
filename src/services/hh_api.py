# src/services/hh_api.py
import httpx
from src.config import config
from src.redis_init import redis


async def get_headers():
    # Логика получения access_token из redis или базы, только без aiogram и bot
    # Пример, если токен хранится в redis как строка:
    access_token = await redis.get('hh_access_token')
    await redis.close()
    if not access_token:
        raise Exception("Нет access_token для hh.ru")
    return {
        "Authorization": f"Bearer {access_token.decode()}"
    }

async def get_resume(resume_id):
    url = f"{config.hh.resume_url}{resume_id}"
    headers = await get_headers()
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
