# src/bot/utils/telegram.py

async def remove_reply_markup_by_state(message, state, msg_id_key="msg_id"):
    """
    Удаляет inline-клавиатуру у сообщения с id, который сохранён в state под ключом msg_id_key.
    Используй для любых вспомогательных сообщений с клавиатурами.

    :param message: aiogram.types.Message
    :param state: FSMContext
    :param msg_id_key: str, ключ под которым лежит message_id в state (по умолчанию "msg_id")
    """
    data = await state.get_data()
    target_msg_id = data.get(msg_id_key)
    if target_msg_id:
        try:
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=target_msg_id,
                reply_markup=None
            )
        except Exception:
            pass
