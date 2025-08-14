from aiogram_dialog import Dialog

from .windows import w_auth, w_ask_url
from .states import AddResumeSG


add_resume_dialog = Dialog(w_auth, w_ask_url)

__all__ = ["add_resume_dialog", "AddResumeSG"]
