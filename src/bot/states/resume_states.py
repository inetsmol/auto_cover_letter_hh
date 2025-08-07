# src/states/user_states.py
from aiogram.fsm.state import StatesGroup, State

class AddResumeStates(StatesGroup):
    waiting_for_resume_url = State()
    waiting_for_positive_keywords = State()
    waiting_for_negative_keywords = State()
