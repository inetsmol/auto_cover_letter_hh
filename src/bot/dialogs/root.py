# src/bot/dialogs/root.py
# aiogram-dialog 2.x
from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import Dialog, Window, LaunchMode
from aiogram_dialog.widgets.text import Const

class RootSG(StatesGroup):
    blank = State()  # окно-заглушка

# Пустое окно. Текст намеренно пустой (незаметное сообщение)
w_blank = Window(Const(""), state=RootSG.blank)

# ВАЖНО: LaunchMode.ROOT => старт такого диалога всегда чистит стек
root_dialog = Dialog(w_blank, launch_mode=LaunchMode.ROOT)

__all__ = ["RootSG", "root_dialog"]
