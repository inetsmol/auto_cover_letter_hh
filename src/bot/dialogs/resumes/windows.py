# src/bot/dialogs/resumes/windows.py
from __future__ import annotations

import operator
from aiogram_dialog import Window
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Select, Button, Back, Row, Column
from aiogram_dialog.widgets.input import MessageInput

from src.bot.dialogs.resume_add.handlers import open_add_dialog
from src.bot.dialogs.resumes.states import ResumesSG
from src.bot.dialogs.resumes.getters import list_getter, manage_getter
from src.bot.dialogs.resumes.handlers import (
    on_resume_selected,
    to_pos_input, to_neg_input,
    toggle_status, ask_delete, do_delete,
    to_main_menu,
    on_pos_words, on_neg_words,
)

# Окно со списком резюме
w_list = Window(
    Format("📄 Ваши резюме ({count}):\nВыберите один из пунктов ниже."),
    Column(
        Select(
            Format("{item[0]}"),                 # текст кнопки = title
            id="resumes",
            items="resumes",                     # берём из list_getter
            item_id_getter=operator.itemgetter(1),  # id = второй элемент (resume_id)
            on_click=on_resume_selected,
        ),
    ),
    Row(
        Button(Const("➕ Добавить резюме"), id="add_resume", on_click=open_add_dialog),
        Button(Const("⬅️ В главное меню"), id="to_main_from_list", on_click=to_main_menu),
    ),
    state=ResumesSG.list,
    getter=list_getter,
)

# Окно управления выбранным резюме
w_manage = Window(
    Format("{card}"),
    Row(
        Button(Const("⚙️ Ключевые слова"), id="edit_pos", on_click=to_pos_input),
        Button(Const("🚫 Слова-исключения"), id="edit_neg", on_click=to_neg_input),
    ),
    Row(
        Button(Const("🔄 Изменить статус"), id="toggle", on_click=toggle_status),
        Button(Const("🗑️ Удалить"), id="delete", on_click=ask_delete),
    ),
    Row(
        Back(Const("⬅️ К списку резюме")),
        Button(Const("⬅️ В главное меню"), id="to_main_from_manage", on_click=to_main_menu),
    ),
    state=ResumesSG.manage,
    getter=manage_getter,
)

# Ввод позитивных ключевых слов
w_pos_input = Window(
    Const(
        "Отправьте ключевые слова через пробелы или запятые.\n"
        "Напр.: <code>Python, Django, FastAPI</code>"
    ),
    MessageInput(on_pos_words),
    Row(
        Back(Const("⬅️ Назад")),
        Button(Const("⬅️ В главное меню"), id="to_main_from_pos", on_click=to_main_menu)
    ),
    state=ResumesSG.pos_input,
)

# Ввод негативных слов
w_neg_input = Window(
    Const(
        "Отправьте слова-исключения через пробелы или запятые.\n"
        "Напр.: <code>1C, PHP, фронтенд</code>"
    ),
    MessageInput(on_neg_words),
    Row(
        Back(Const("⬅️ Назад")),
        Button(Const("⬅️ В главное меню"), id="to_main_from_neg", on_click=to_main_menu)
    ),
    state=ResumesSG.neg_input,
)

# Подтверждение удаления
w_confirm = Window(
    Const("Удалить резюме безвозвратно?"),
    Row(
        Button(Const("✅ Да, удалить"), id="confirm_del", on_click=do_delete),
        Back(Const("↩️ Нет")),
    ),
    Row(Button(Const("⬅️ В главное меню"), id="to_main_from_confirm", on_click=to_main_menu)),
    state=ResumesSG.confirm_delete,
)
