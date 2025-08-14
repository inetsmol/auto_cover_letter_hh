from aiogram_dialog import Dialog

from .windows import w_ask_url, w_result
from .states import AddResumeSG


add_resume_dialog = Dialog(w_ask_url, w_result)

__all__ = ["add_resume_dialog", "AddResumeSG"]
