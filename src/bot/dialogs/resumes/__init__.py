# src/bot/dialogs/resumes/__init__.py
from aiogram_dialog import Dialog

from .windows import w_list, w_manage, w_pos_input, w_neg_input, w_confirm
from .states import ResumesSG

# Экспортируем готовый Dialog и состояния
resumes_dialog = Dialog(w_list, w_manage, w_pos_input, w_neg_input, w_confirm)

__all__ = ["resumes_dialog", "ResumesSG"]
