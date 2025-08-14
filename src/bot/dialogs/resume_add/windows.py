# src/bot/dialogs/resume_add/windows.py
from aiogram_dialog import Window
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Row, Url
from aiogram_dialog.widgets.input import MessageInput

from src.bot.dialogs.resume_add.getters import result_getter, auth_getter
from src.bot.dialogs.resume_add.states import AddResumeSG
from src.bot.dialogs.resume_add.handlers import (
    on_url_input, to_manage_resume, to_resumes_list, to_main_menu, check_auth_and_go,
)

# ─────────────────────────────────────────────────────────────────────────────
# Окно «Нужна авторизация»
# ─────────────────────────────────────────────────────────────────────────────
w_auth = Window(
    Const(
        "Чтобы добавить резюме, нужно авторизоваться на hh.ru и разрешить боту доступ от вашего имени.\n\n"
        "1) Нажмите кнопку ниже и завершите вход на hh.ru.\n"
        "2) Затем вернитесь в бот (или нажмите «Я авторизовался»)."
    ),
    Row(
        Url(Const("🔐 Авторизоваться на hh.ru"), url=Format("{auth_url}"), id="auth_url_btn"),
    ),
    Row(
        Button(Const("🔄 Я авторизовался"), id="auth_check", on_click=check_auth_and_go),
        Button(Const("⬅️ Отмена"), id="auth_cancel", on_click=to_main_menu),
    ),
    state=AddResumeSG.auth,
    getter=auth_getter,
)

# ─────────────────────────────────────────────────────────────────────────────
# Окно ввода ссылки
# ─────────────────────────────────────────────────────────────────────────────
w_ask_url = Window(
    Const(
        "Пожалуйста, пришлите ссылку на своё резюме hh.ru в формате:\n"
        "<code>https://hh.ru/resume/ВАШ_ID</code>"
    ),
    MessageInput(on_url_input),
    Row(
        Button(Const("⬅️ В главное меню"), id="to_main_from_add_ask", on_click=to_main_menu),
    ),
    state=AddResumeSG.ask_url,
)