# src/bot_init.py
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.config import config
from src.redis_init import storage

# Инициализируем бот и диспетчер
bot = Bot(token=config.bot.token.get_secret_value(), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)

# Импортируем и регистрируем bot-хендлеры
from src.handlers.bot import routers as bot_routers
for router in bot_routers:
    dp.include_router(router)