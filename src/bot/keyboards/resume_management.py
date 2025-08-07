# src/bot/keyboards/resume_management.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def resume_main_menu():
    """
    Главное меню раздела "Мои резюме" (только общие действия).
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить резюме", callback_data="resume:add"),
        ],
        [
            InlineKeyboardButton(text="⬅️ В главное меню", callback_data="menu:main"),
        ],
    ])


def resumes_list_menu(resumes: list[dict]):
    """
    Список резюме с кнопками для управления каждым резюме.
    resumes: [{'id': '...', 'title': '...'}]
    """
    buttons = [
        [InlineKeyboardButton(text=res['title'], callback_data=f"resume:manage:{res['id']}")]
        for res in resumes
    ]

    buttons.append(
        [
            InlineKeyboardButton(text="➕ Добавить резюме", callback_data="resume:add"),
            InlineKeyboardButton(text="⬅️ В главное меню", callback_data="menu:main")
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def manage_resume_menu(resume_id: str):
    """
    Клавиатура для управления одним резюме.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚙️ Ключевые слова", callback_data=f"resume:keywords:{resume_id}"),
            InlineKeyboardButton(text="🚫 Слова-исключения", callback_data=f"resume:negative:{resume_id}")
        ],
        [
            InlineKeyboardButton(text="🔄 Изменить статус", callback_data=f"resume:status:{resume_id}"),
        ],
        [
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"resume:delete:{resume_id}"),
        ],
        [
            InlineKeyboardButton(text="⬅️ К списку резюме", callback_data="menu:resumes"),
            InlineKeyboardButton(text="⬅️ В главное меню", callback_data="menu:main"),
        ],
    ])
