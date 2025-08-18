# src/services/resume/parser.py
import re
from typing import List


def extract_keywords(text: str) -> List[str]:
    """
    Извлекает ключевые слова из текста

    Args:
        text: Текст для извлечения ключевых слов

    Returns:
        List[str]: Список уникальных ключевых слов
    """
    if not text:
        return []

    pattern = r"""
        C\+\+                   # C++
        | C\#                   # C#
        | \.NET                 # .NET
        | [A-Za-z]+\.js         # Node.js, React.js и т.п.
        | [A-Za-zА-Яа-яёЁ]{2,}     # Слова из латиницы или кириллицы (не меньше двух)
        | \d+[A-Za-zА-Яа-яёЁ]+     # Слова типа 1С, 2ГИС
    """

    # Поиск всех совпадений
    matches = re.findall(pattern, text, re.X)

    # Уникальные, без чисел
    keywords = []
    for word in matches:
        if word and not word.isdigit():
            keywords.append(word)
    # Оставляем только уникальные, в порядке появления
    return list(dict.fromkeys(keywords))


def extract_resume_description_from_json(resume_data):
    """
    Извлекает информацию о резюме из JSON-ответа HeadHunter API

    Args:
        resume_data (dict): JSON-ответ от API HeadHunter для резюме

    Returns:
        str: Форматированное резюме
    """

    # Основная информация
    first_name = resume_data.get('first_name', '')
    last_name = resume_data.get('last_name', '')
    middle_name = resume_data.get('middle_name', '')

    # Формируем полное имя
    full_name_parts = [first_name, middle_name, last_name]
    full_name = ' '.join(filter(None, full_name_parts))

    title = resume_data.get('title', 'Специалист')

    # Возраст
    age_info = ""
    age = resume_data.get('age')
    if age:
        age_info = f", {age} лет"

    # Локация
    area = resume_data.get('area', {}).get('name', '')

    # Зарплатные ожидания
    salary_info = ""
    salary = resume_data.get('salary')
    if salary:
        amount = salary.get('amount')
        currency = salary.get('currency', 'RUR')
        if amount:
            salary_info = f"Зарплатные ожидания: {amount:,} {currency}"

    # Тип занятости и график
    employment = resume_data.get('employment', {}).get('name', '')
    schedule = resume_data.get('schedule', {}).get('name', '')

    # Готовность к переезду и командировкам
    relocation = resume_data.get('relocation', {}).get('type', {}).get('name', '')
    business_trip = resume_data.get('business_trip_readiness', {}).get('name', '')

    # Контактная информация
    contacts = []
    for contact in resume_data.get('contact', []):
        contact_type = contact.get('type', {}).get('name', '')
        if contact_type == 'Эл. почта':
            email = contact.get('value', '')
            if email:
                contacts.append(f"Email: {email}")
        elif contact_type == 'Мобильный телефон':
            phone = contact.get('value', {}).get('formatted', '')
            if phone:
                comment = contact.get('comment', '')
                phone_info = f"Телефон: {phone}"
                if comment:
                    phone_info += f" ({comment})"
                contacts.append(phone_info)

    # Дополнительные способы связи
    sites = resume_data.get('site', [])
    for site in sites:
        site_type = site.get('type', {}).get('name', '')
        site_url = site.get('url', '')
        if site_url:
            contacts.append(f"{site_type}: {site_url}")

    # Образование
    education_info = []
    education = resume_data.get('education', {})

    # Уровень образования
    education_level = education.get('level', {}).get('name', '')
    if education_level:
        education_info.append(f"Уровень образования: {education_level}")

    # Основное образование
    primary_education = education.get('primary', [])
    for edu in primary_education:
        edu_parts = []
        year = edu.get('year')
        if year:
            edu_parts.append(str(year))

        name = edu.get('name', '')
        if name:
            edu_parts.append(name)

        organization = edu.get('organization', '')
        if organization:
            edu_parts.append(organization)

        result = edu.get('result', '')
        if result:
            edu_parts.append(f"Специальность: {result}")

        if edu_parts:
            education_info.append(' - '.join(edu_parts))

    # Дополнительное образование
    additional_education = education.get('additional', [])
    if additional_education:
        education_info.append("Дополнительное образование:")
        for edu in additional_education:
            edu_name = edu.get('name', '')
            edu_org = edu.get('organization', '')
            edu_year = edu.get('year', '')

            edu_parts = []
            if edu_year:
                edu_parts.append(str(edu_year))
            if edu_name:
                edu_parts.append(edu_name)
            if edu_org:
                edu_parts.append(edu_org)

            if edu_parts:
                education_info.append(f"  • {' - '.join(edu_parts)}")

    # Опыт работы
    experience_info = []
    experience = resume_data.get('experience', [])

    total_experience = resume_data.get('total_experience', {})
    months = total_experience.get('months', 0)
    if months:
        years = months // 12
        remaining_months = months % 12
        exp_text = []
        if years:
            exp_text.append(f"{years} лет")
        if remaining_months:
            exp_text.append(f"{remaining_months} мес.")
        if exp_text:
            experience_info.append(f"Общий стаж: {' '.join(exp_text)}")

    for exp in experience:
        exp_parts = []

        # Период работы
        start = exp.get('start', '')
        end = exp.get('end', '')
        if start:
            period = start
            if end:
                period += f" - {end}"
            else:
                period += " - настоящее время"
            exp_parts.append(period)

        # Должность
        position = exp.get('position', '')
        if position:
            exp_parts.append(position)

        # Компания
        company = exp.get('company', '')
        if company:
            exp_parts.append(company)

        # Описание обязанностей
        description = exp.get('description', '')

        if exp_parts:
            experience_info.append(' - '.join(exp_parts))
            if description:
                experience_info.append(f"  Обязанности: {description}")

    # Языки
    languages_info = []
    languages = resume_data.get('language', [])
    for lang in languages:
        lang_name = lang.get('name', '')
        lang_level = lang.get('level', {}).get('name', '')
        if lang_name:
            lang_text = lang_name
            if lang_level:
                lang_text += f" - {lang_level}"
            languages_info.append(lang_text)

    # Ключевые навыки
    skills_info = []

    # Навыки из skill_set
    skill_set = resume_data.get('skill_set', [])
    if skill_set:
        skills_info.extend(skill_set)

    # Навыки из текстового поля
    skills_text = resume_data.get('skills', '')
    if skills_text:
        skills_info.append(skills_text)

    # Профессиональные роли
    professional_roles = []
    for role in resume_data.get('professional_roles', []):
        role_name = role.get('name', '')
        if role_name:
            professional_roles.append(role_name)

    # Формируем итоговое резюме
    resume_parts = []

    # Заголовок
    header_parts = [full_name]
    if area:
        header_parts.append(area)
    if age_info:
        header_parts[-1] += age_info

    resume_parts.append(' | '.join(header_parts))
    resume_parts.append(title)

    if salary_info:
        resume_parts.append(salary_info)

    # Контакты
    if contacts:
        resume_parts.append("\nКОНТАКТЫ:")
        resume_parts.extend(contacts)

    # Условия работы
    work_conditions = []
    if employment:
        work_conditions.append(f"Занятость: {employment}")
    if schedule:
        work_conditions.append(f"График: {schedule}")
    if relocation:
        work_conditions.append(f"Переезд: {relocation}")
    if business_trip:
        work_conditions.append(f"Командировки: {business_trip}")

    if work_conditions:
        resume_parts.append("\nУСЛОВИЯ РАБОТЫ:")
        resume_parts.extend(work_conditions)

    # Профессиональные роли
    if professional_roles:
        resume_parts.append(f"\nПРОФЕССИОНАЛЬНЫЕ РОЛИ: {', '.join(professional_roles)}")

    # Образование
    if education_info:
        resume_parts.append("\nОБРАЗОВАНИЕ:")
        resume_parts.extend(education_info)

    # Опыт работы
    if experience_info:
        resume_parts.append("\nОПЫТ РАБОТЫ:")
        resume_parts.extend(experience_info)

    # Языки
    if languages_info:
        resume_parts.append(f"\nЯЗЫКИ: {', '.join(languages_info)}")

    # Навыки
    if skills_info:
        resume_parts.append(f"\nКЛЮЧЕВЫЕ НАВЫКИ: {', '.join(skills_info)}")

    return "\n".join(resume_parts)


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