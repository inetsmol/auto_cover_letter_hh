# src/services/hh/auth/token_manager.py

from hh_api.auth import TokenManager

from src.services.hh.auth.oauth_config import oauth_cfg
from src.services.hh.auth.token_store import TortoiseTokenStore, store

# Ваш User-Agent обязателен для всех запросов к hh API
USER_AGENT = "auto-cover-letter-bot/1.0"

# Менеджер токенов (универсальный — работает с любым KeyedTokenStore)
tm = TokenManager(oauth_cfg, store, user_agent=USER_AGENT)