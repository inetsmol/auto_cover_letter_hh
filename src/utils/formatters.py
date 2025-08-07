# src/bot/utils/formatters.py

def format_resume_card(resume):
    """
    Генерирует подробный текст о резюме для показа пользователю.
    """
    title = (resume.resume_json or {}).get('title', 'Без названия')
    positive_keywords = ', '.join(resume.positive_keywords or [])
    negative_keywords = ', '.join(resume.negative_keywords or [])

    status_label = "🟢 Активно" if resume.status == "active" else "📁 В архиве"
    status_hint = (
        "\n<i>Нажмите “Изменить статус”, чтобы "
        f"{'отправить резюме в архив' if resume.status == 'active' else 'сделать резюме активным'}.</i>"
    )

    text = (
        f"<b>{title}</b>\n"
        f"ID: <code>{resume.id}</code>\n"
        f"Статус: {status_label}{status_hint}\n"
        f"Ключевые слова: {positive_keywords or 'нет'}\n"
    )
    if negative_keywords:
        text += f"Исключения: {negative_keywords}\n"
    return text
