# src/handlers/hh_auth.py
from typing import Optional

from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, JSONResponse

from src.config import config
from src.services.hh.auth.token_manager import tm

auth_router = APIRouter()


@auth_router.get("/hh-bot/")
async def callback(request: Request):
    """
    OAuth2 callback от hh.ru:
    - code: авторизационный код
    - state: Telegram user_id (мы передали его при генерации ссылки)
    """
    code: Optional[str] = request.query_params.get("code")
    state: Optional[str] = request.query_params.get("state")
    if not code or not state:
        return JSONResponse({"error": "Missing 'code' or 'state'"}, status_code=status.HTTP_400_BAD_REQUEST)

    try:
        subject = int(state)
        await tm.exchange_code(subject=subject, code=code)
    except Exception as e:
        return HTMLResponse(f"<html><body>Ошибка авторизации: {e}</body></html>", status_code=400)

    # ❗️Не пишем ничего в Telegram.
    # Вместо этого сразу отправляем пользователя обратно в бота на deep-link,
    # который открывает окно ввода ссылки (AddResumeSG.ask_url).
    bot_username = config.bot.username  # убедитесь, что задано в конфиге
    tg_url = f"tg://resolve?domain={bot_username}&start=add_resume"

    # быстрый редирект в Telegram-клиент + запасная ссылка
    html = f"""
    <html>
      <head>
        <meta http-equiv="refresh" content="0; url={tg_url}" />
      </head>
      <body>
        <p>Перенаправляем в Telegram… Если не произошло автоматически, нажмите:</p>
        <p><a href="{tg_url}">Открыть бота</a></p>
      </body>
    </html>
    """
    return HTMLResponse(html)