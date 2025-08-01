# src/fastapi_app.py
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from aiogram.types import Update

from src.bot_init import bot, dp
from src.handlers.base import base_router
from src.handlers.hh_auth import auth_router
from src.services.startup import on_startup, on_shutdown
from src.config import config


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    await on_startup()
    await bot.set_webhook(
        config.bot.webhook_url,
        secret_token=config.bot.webhook_secret.get_secret_value()
    )
    yield
    # shutdown
    await bot.delete_webhook()
    await on_shutdown()

app = FastAPI(lifespan=lifespan)

app.include_router(base_router)
app.include_router(auth_router)


# --- webhook route ---
@app.post(config.bot.webhook_path)
async def webhook(request: Request):
    # Проверка секретного токена Telegram (если используется)
    secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret_token != config.bot.webhook_secret.get_secret_value():
        return Response(status_code=status.HTTP_403_FORBIDDEN)

    # Получаем update
    data = await request.json()
    update = Update.model_validate(data)

    # Обрабатываем через диспетчер
    await dp.feed_update(bot, update, webhook=True)
    return Response(status_code=status.HTTP_200_OK)
