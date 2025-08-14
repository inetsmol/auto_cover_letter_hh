from __future__ import annotations

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode

from src.bot.keyboards.main_menu import get_main_menu
from src.config import config

async def close_all_dialogs_and_show_main_menu(cq: CallbackQuery, dialog_manager: DialogManager) -> None:
    """
    Закрыть ВСЕ диалоги (жёсткая очистка стека), удалить/обнулить инлайн-клавиатуру
    у последнего сообщения окна и показать главное меню (ReplyKeyboard).
    """
    # 1) Попробуем удалить сообщение с кнопками (самый надёжный способ «обезвредить» старые callback'и)
    try:
        await cq.message.delete()
    except Exception:
        # Если удалить нельзя (нет прав/устарело) — хотя бы уберём клавиатуру
        try:
            await cq.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

    # 2) Сбросить стек диалогов.
    # Способ А: запустить заглушку-диалог ROOT и сразу закрыть (см. пункт 2 ниже),
    # Способ Б (если не хочешь заводить ROOT): просто попытаться закрыть текущий контекст.
    try:
        from src.bot.dialogs.root import RootSG  # ленивый импорт, чтобы не плодить циклы
        await dialog_manager.start(RootSG.blank, mode=StartMode.RESET_STACK)
        await dialog_manager.done()
    except Exception:
        # Если ROOT не подключён — закроем «текущий» (если он есть)
        try:
            await dialog_manager.done()
        except Exception:
            pass

    # 3) Показать главное меню (ReplyKeyboard)
    is_admin = cq.from_user.id in config.bot.admin_ids
    await cq.message.answer("Главное меню:", reply_markup=get_main_menu(is_admin))
