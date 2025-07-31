# src/db/config.py
from src.config import config

TORTOISE_ORM = {
    "connections": {"default": config.database.async_url},
    "apps": {
        "models": {
            "models": ["src.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}