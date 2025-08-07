# src/handlers/hh_auth.py
import datetime
from datetime import timedelta

import httpx
from fastapi import APIRouter
from starlette.requests import Request

from src.config import config
from src.models import HHToken
from src.redis_init import redis

auth_router = APIRouter()


@auth_router.get("/hh-bot/")
async def callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return {"error": "Authorization code not found in redirect"}

    await exchange_code_for_token(code)
    return {"status": "success", "message": "Authorization completed"}


async def exchange_code_for_token(code: str):
    """Обменивает код авторизации на токены"""
    url = "https://hh.ru/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": config.hh.client_id.get_secret_value(),
        "client_secret": config.hh.client_secret.get_secret_value(),
        "code": code,
        "redirect_uri": config.hh.redirect_uri
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=data)
        if response.status_code != 200:
            return {"error": f"Failed to get tokens: {response.text}"}

        tokens = response.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 3600)
        expires_at = datetime.datetime.now(datetime.UTC) + timedelta(seconds=expires_in)

        # Сохраняем в базу
        await HHToken.update_or_create(
            id=1,
            defaults={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
            }
        )

        # Сохраняем в Redis
        await redis.set(config.redis.access_token_key, access_token, ex=expires_in)
        return {"status": "success"}