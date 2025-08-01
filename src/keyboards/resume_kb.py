from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_resume_actions_inline_kb(resume_id: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Ключевые слова",
                    callback_data=f"add_positive:{resume_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="➖ Негативные слова",
                    callback_data=f"add_negative:{resume_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚀 Запустить отправку откликов",
                    callback_data=f"start_apply:{resume_id}"
                )
            ],
        ]
    )
