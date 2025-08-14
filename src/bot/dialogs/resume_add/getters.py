from aiogram_dialog import DialogManager


async def result_getter(dialog_manager: DialogManager, **kwargs):
    """Пробрасываем значения из dialog_data в корень данных окна."""
    dd = dialog_manager.dialog_data
    return {
        # безопасные значения по умолчанию, чтобы не падать при повторном рендере
        "card": dd.get("card", "❗️Данные не найдены. Отправьте ссылку ещё раз."),
        "keywords": dd.get("keywords", "—"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Геттер для окна авторизации: отдаём auth_url из start_data/dialog_data
# ─────────────────────────────────────────────────────────────────────────────
async def auth_getter(dialog_manager: DialogManager, **kwargs):
    """
    Возвращает ссылку для авторизации на hh.ru.
    При первом заходе берём из start_data, затем кешируем в dialog_data.
    """
    dd = dialog_manager.dialog_data
    url = dd.get("auth_url") or (dialog_manager.start_data or {}).get("auth_url")
    if not url:
        # На всякий случай — сгенерируем «на лету»
        from src.services.hh.auth.token_manager import tm
        url = tm.authorization_url(state=str(dialog_manager.event.from_user.id))
    dd["auth_url"] = url
    return {"auth_url": url}