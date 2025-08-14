# src/bot/dialogs/resume_add/states.py
from aiogram.fsm.state import StatesGroup, State

class AddResumeSG(StatesGroup):
    """
    Состояния диалога добавления резюме.
    """
    ask_url = State()     # окно ожидания ссылки
    result = State()      # результат (карточка резюме + кнопки)
