# src/bot/dialogs/resume_add/windows.py
from aiogram_dialog import Window
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Row
from aiogram_dialog.widgets.input import MessageInput

from src.bot.dialogs.resume_add.getters import result_getter
from src.bot.dialogs.resume_add.states import AddResumeSG
from src.bot.dialogs.resume_add.handlers import (
    on_url_input, to_manage_resume, to_resumes_list, to_main_menu,
)

# Окно ввода ссылки
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

# Окно результата: карточка резюме + кнопки навигации
w_result = Window(
    Format("{card}"),
    Row(
        Button(Const("⚙️ Управление резюме"), id="to_manage_after_add", on_click=to_manage_resume),
    ),
    Row(
        Button(Const("📄 К списку резюме"), id="to_list_after_add", on_click=to_resumes_list),
        Button(Const("⬅️ В главное меню"), id="to_main_after_add", on_click=to_main_menu),
    ),
    state=AddResumeSG.result,
    getter=result_getter,
)
