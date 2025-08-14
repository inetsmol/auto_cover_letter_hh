# src/bot/dialogs/resume_add/states.py
from aiogram.fsm.state import StatesGroup, State

class AddResumeSG(StatesGroup):
    """
    Состояния диалога добавления резюме.
    """
    auth = State()  # окно «нужна авторизация на hh.ru»
    ask_url = State()  # окно ожидания ссылки на резюме
    result = State()  # (опционально) окно результата
