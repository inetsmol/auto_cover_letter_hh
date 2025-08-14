# src/bot_init.py
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram_dialog import setup_dialogs

from src.bot.dialogs.root import root_dialog
from src.bot.dialogs.resume_add import add_resume_dialog
from src.bot.dialogs.resumes import resumes_dialog
from src.bot.handlers.resume.entry import router as resumes_entry_router
from src.bot.dialogs.resume_add.handlers import router as resume_add_inline_router
from src.config import config
from src.redis_init import storage

# Инициализируем бот и диспетчер
bot = Bot(token=config.bot.token.get_secret_value(), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)

dp.include_router(root_dialog)
dp.include_router(resume_add_inline_router)
# триггер из ReplyKeyboard
dp.include_router(resumes_entry_router)
# Подключаем сам диалог (в 2.x каждый Dialog — это Router)
dp.include_router(resumes_dialog)
dp.include_router(add_resume_dialog)


# Импортируем и регистрируем bot-хендлеры
from src.bot.handlers import routers as bot_routers
for router in bot_routers:
    dp.include_router(router)


# инициализация aiogram-dialog
setup_dialogs(dp)
