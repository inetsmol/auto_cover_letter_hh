# src/services/hh/auth/token_manager.py
from src.config import config

from hh_api.auth import OAuthConfig, TokenManager

from src.services.hh.auth.token_store import TortoiseTokenStore

# Ваш User-Agent обязателен для всех запросов к hh API
USER_AGENT = "auto-cover-letter-bot/1.0"


# Рекомендуется хранить секреты в окружении (или pydantic-settings)
CLIENT_ID = config.hh.client_id.get_secret_value()
CLIENT_SECRET = config.hh.client_secret.get_secret_value()
REDIRECT_URI = config.hh.redirect_uri


# Конфиг OAuth (правильный token_url уже внутри класса из примера)
oauth_cfg = OAuthConfig(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
)

# JSON сторадж: на каждого пользователя — отдельный файл <subject>.json
store = TortoiseTokenStore()

# Менеджер токенов (универсальный — работает с любым KeyedTokenStore)
tm = TokenManager(oauth_cfg, store, user_agent=USER_AGENT)