import httpx
from openai import AsyncOpenAI

from src.ai.prompt import generate_system_prompt, user_prompt
from src.config import config


async def generate_cover_letter(resume_text, vacancy_text):
    system_prompt = generate_system_prompt(resume_text, vacancy_text)
    # Здесь предполагается, что user_prompt где-то заранее определён
    # Если нет — добавь аргумент user_prompt в функцию или сформируй внутри

    if config.ai.proxy_url:
        async_client = httpx.AsyncClient(proxy=config.ai.proxy_url)
        client = AsyncOpenAI(api_key=config.ai.openai_api_key, http_client=async_client)
    else:
        client = AsyncOpenAI(api_key=config.ai.openai_api_key)

    response = await client.chat.completions.create(
        model="gpt-4-1-mini",
        temperature=0.5,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    # Если использовал свой AsyncClient — не забудь закрыть его:
    if config.ai.proxy_url:
        await async_client.aclose()

    return response.choices[0].message.content
