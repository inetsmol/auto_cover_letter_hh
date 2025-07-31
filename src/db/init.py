# src/db/init.py
import logging
from tortoise import Tortoise
from src.db.config import TORTOISE_ORM

logger = logging.getLogger(__name__)


async def init_db():
    """Инициализация базы данных"""
    try:
        await Tortoise.init(config=TORTOISE_ORM)
    except Exception as e:
        logger.error(e)


async def close_db():
    """Закрытие соединения с базой данных"""
    await Tortoise.close_connections()