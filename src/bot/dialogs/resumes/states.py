# src/bot/dialogs/resumes/states.py
# aiogram-dialog 2.x
from aiogram.fsm.state import StatesGroup, State

class ResumesSG(StatesGroup):
    """
    Состояния диалога «Резюме».
    """
    list = State()           # список резюме
    manage = State()         # управление выбранным резюме
    pos_input = State()      # ввод позитивных ключевых слов
    neg_input = State()      # ввод негативных слов
    confirm_delete = State() # подтверждение удаления
