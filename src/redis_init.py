from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage, Redis
from src.config import config

redis = Redis.from_url(config.redis.dsn)
storage = RedisStorage(redis=redis, key_builder=DefaultKeyBuilder(with_destiny=True, with_bot_id=True))