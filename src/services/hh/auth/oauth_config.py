
from hh_api.auth import OAuthConfig

from src.config import config

CLIENT_ID = config.hh.client_id.get_secret_value()
CLIENT_SECRET = config.hh.client_secret.get_secret_value()
REDIRECT_URI = config.hh.redirect_uri
USER_AGENT = "auto-cover-letter-bot/1.0"

# Конфиг OAuth (правильный token_url уже внутри класса из примера)
oauth_cfg = OAuthConfig(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
)
