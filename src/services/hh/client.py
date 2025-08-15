from hh_api.client import HHClient

from src.services.hh.auth.token_manager import tm

USER_AGENT = "auto-cover-letter-bot/1.0"


hhc = HHClient(tm=tm, user_agent=USER_AGENT)