import re

import httpx

from src.config import config
from src.hh_auth import get_headers


async def get_resume(resume_id):
    url = f"{config.hh.resume_url}{resume_id}"
    headers = await get_headers()
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()  # Вызывает исключение для кодов 4xx/5xx
        return response.json()


def extract_keywords(text: str) -> list[str]:
    if not text:
        return []

    # Шаблон для IT-ключей:
    # - C++
    # - C#
    # - .NET (с точкой!)
    # - Node.js, React.js (любое слово .js)
    # - Слова из латиницы (от двух букв и более)
    pattern = r"""
        C\+\+            # C++
        | C\#            # C#
        | \.NET          # .NET
        | [A-Za-z]+\.js  # Node.js, React.js и т.п.
        | [A-Za-z]{2,}   # Остальные слова из букв (не меньше двух)
    """

    # Поиск всех совпадений
    matches = re.findall(pattern, text, re.X)

    # Уникальные, без чисел
    keywords = []
    for word in matches:
        if word and not any(char.isdigit() for char in word):
            keywords.append(word)
    # Оставляем только уникальные, в порядке появления
    return list(dict.fromkeys(keywords))


if __name__ == "__main__":
    title = "Python Backend Developer | FastAPI, Django/ PostgreSQL - Docker · Redis • SQLAlchemy; Git"
    print(extract_keywords(title))
    # ['Python Backend Developer', 'FastAPI', 'Django', 'PostgreSQL', 'Docker', 'Redis', 'SQLAlchemy', 'Git']

    title2 = "Product Owner   Agile Scrum · Jira/Confluence • Trello | коммуникации"
    print(extract_keywords(title2))
    # ['Product Owner', 'Agile Scrum', 'Jira', 'Confluence', 'Trello', 'коммуникации']

    title3 = "Python Backend Developer, Product Owner, Agile Scrum, FastAPI, Django, C++, C#, Node.js, .NET, React.js, TypeScript, Java 17, Python 3.10"
    print(extract_keywords(title3))
    # ['Python', 'Backend', 'Developer', 'Product', 'Owner', 'Agile', 'Scrum', 'FastAPI', 'Django', 'C++', 'C#', 'Node.js', '.NET', 'React.js', 'TypeScript', 'Java', '17', '3.10']
