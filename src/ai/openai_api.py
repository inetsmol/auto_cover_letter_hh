# src/ai/openai_api.py
import httpx
from openai import AsyncOpenAI

from src.ai.prompt import generate_system_prompt, user_prompt
from src.config import config


async def generate_cover_letter(resume_text: str, vacancy_text: str) -> str:
    """
    Генерирует сопроводительное письмо используя OpenAI API

    Args:
        resume_text: Текст резюме
        vacancy_text: Описание вакансии

    Returns:
        str: Сгенерированное сопроводительное письмо
    """
    system_prompt = generate_system_prompt(resume_text, vacancy_text)

    if config.ai.proxy_url:
        async_client = httpx.AsyncClient(proxy=config.ai.proxy_url)
        client = AsyncOpenAI(api_key=config.ai.openai_api_key.get_secret_value(), http_client=async_client)
    else:
        client = AsyncOpenAI(api_key=config.ai.openai_api_key.get_secret_value())

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.5,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        return response.choices[0].message.content

    finally:
        # Если использовал свой AsyncClient — не забудь закрыть его:
        if config.ai.proxy_url:
            await async_client.aclose()