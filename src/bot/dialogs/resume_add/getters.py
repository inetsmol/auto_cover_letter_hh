from aiogram_dialog import DialogManager


async def result_getter(dialog_manager: DialogManager, **kwargs):
    """Пробрасываем значения из dialog_data в корень данных окна."""
    dd = dialog_manager.dialog_data
    return {
        # безопасные значения по умолчанию, чтобы не падать при повторном рендере
        "card": dd.get("card", "❗️Данные не найдены. Отправьте ссылку ещё раз."),
        "keywords": dd.get("keywords", "—"),
    }