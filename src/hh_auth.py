# src/hh_auth.py
from src.auth.access_token import get_access_token


async def get_headers():
    access_token = await get_access_token()
    return {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "HH-Job-Bot (CodeGPT)"
    }
