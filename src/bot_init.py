# src/bot_init.py
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage, Redis

from src.config import config

redis = Redis.from_url(config.redis.dsn)
storage = RedisStorage(redis=redis, key_builder=DefaultKeyBuilder(with_destiny=True, with_bot_id=True))

# Инициализируем бот и диспетчер
bot = Bot(token=config.bot.token.get_secret_value(), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)

# Импортируем и регистрируем bot-хендлеры
from src.handlers.bot import routers as bot_routers
for router in bot_routers:
    dp.include_router(router)