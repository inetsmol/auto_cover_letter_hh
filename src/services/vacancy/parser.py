def extract_job_description_from_vacancy(vacancy_data):
    """
    Извлекает описание вакансии из JSON-ответа HeadHunter API

    Args:
        vacancy_data (dict): JSON-ответ от API HeadHunter

    Returns:
        str: Форматированное описание вакансии
    """

    # Извлекаем основную информацию
    position = vacancy_data.get('name', 'Не указана')
    company = vacancy_data.get('employer', {}).get('name', 'Не указана')
    description = vacancy_data.get('description', '')

    # Зарплата
    salary_info = ""
    salary = vacancy_data.get('salary')
    if salary:
        from_salary = salary.get('from')
        to_salary = salary.get('to')
        currency = salary.get('currency', 'RUR')

        if from_salary and to_salary:
            salary_info = f"от {from_salary:,} до {to_salary:,} {currency}"
        elif from_salary:
            salary_info = f"от {from_salary:,} {currency}"
        elif to_salary:
            salary_info = f"до {to_salary:,} {currency}"

    # Опыт работы
    experience = vacancy_data.get('experience', {}).get('name', 'Не указан')

    # Тип занятости
    employment = vacancy_data.get('employment', {}).get('name', 'Не указан')

    # График работы
    schedule = vacancy_data.get('schedule', {}).get('name', 'Не указан')

    # Ключевые навыки
    key_skills = [skill['name'] for skill in vacancy_data.get('key_skills', [])]

    # Языки
    languages = []
    for lang in vacancy_data.get('languages', []):
        lang_name = lang.get('name', '')
        lang_level = lang.get('level', {}).get('name', '')
        if lang_name:
            languages.append(f"{lang_name} ({lang_level})" if lang_level else lang_name)

    # Локация
    location_info = ""
    address = vacancy_data.get('address')
    if address:
        city = address.get('city', '')
        street = address.get('street', '')
        building = address.get('building', '')
        metro_stations = [station.get('station_name', '') for station in address.get('metro_stations', [])]

        location_parts = []
        if city:
            location_parts.append(city)
        if street:
            street_full = f"{street}"
            if building:
                street_full += f", {building}"
            location_parts.append(street_full)
        if metro_stations:
            location_parts.append(f"м. {', '.join(metro_stations)}")

        location_info = ", ".join(location_parts)

    # Формируем итоговое описание
    job_description_parts = [
        f"ВАКАНСИЯ: {position}",
        f"КОМПАНИЯ: {company}",
    ]

    if salary_info:
        job_description_parts.append(f"ЗАРПЛАТА: {salary_info}")

    job_description_parts.extend([
        f"ОПЫТ РАБОТЫ: {experience}",
        f"ТИП ЗАНЯТОСТИ: {employment}",
        f"ГРАФИК РАБОТЫ: {schedule}",
    ])

    if location_info:
        job_description_parts.append(f"ЛОКАЦИЯ: {location_info}")

    if key_skills:
        skills_text = ", ".join(key_skills)
        job_description_parts.append(f"КЛЮЧЕВЫЕ НАВЫКИ: {skills_text}")

    if languages:
        languages_text = ", ".join(languages)
        job_description_parts.append(f"ЯЗЫКИ: {languages_text}")

    if description:
        # Удаляем HTML-теги из описания (базово)
        import re
        clean_description = re.sub(r'<[^>]+>', '', description)
        clean_description = re.sub(r'\s+', ' ', clean_description).strip()
        job_description_parts.append(f"\nОПИСАНИЕ ВАКАНСИИ:\n{clean_description}")

    return "\n".join(job_description_parts)