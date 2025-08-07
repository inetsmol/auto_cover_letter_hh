# src/services/hh_client.py
"""
Централизованный клиент для работы с API HeadHunter.
"""
import asyncio
import datetime
import httpx
from typing import Optional, Dict, Any

from src.config import config
from src.redis_init import redis


class HHAPIClient:
    """Клиент для работы с API HeadHunter"""

    def __init__(self):
        self._access_token: Optional[str] = None

    async def get_access_token(self, timeout: int = 60) -> str:
        """
        Получает access token для API HH.

        Args:
            timeout: Таймаут ожидания токена в секундах

        Returns:
            str: Access token

        Raises:
            Exception: Если токен не удалось получить
        """
        # 1. Пробуем достать токен из Redis
        access_token = await redis.get(config.redis.access_token_key)
        if access_token:
            return access_token.decode()

        # 2. Пробуем достать из базы
        from src.models import HHToken

        tokens = await HHToken.get_or_none(id=1)
        if not tokens:
            # Нужна авторизация - отправляем уведомление
            await self._request_authorization()

            # Ожидание токена в Redis (polling)
            waited = 0
            while waited < timeout:
                await asyncio.sleep(1)
                waited += 1
                access_token = await redis.get(config.redis.access_token_key)
                if access_token:
                    return access_token.decode()
            raise Exception("Авторизация не завершена: токен не получен за отведённое время")

        # 3. Проверяем актуальность токена
        if (tokens.access_token and
                tokens.expires_at and
                tokens.expires_at > datetime.datetime.now(datetime.UTC)):
            # Кладём в Redis с TTL
            ttl = int((tokens.expires_at - datetime.datetime.now(datetime.UTC)).total_seconds())
            await redis.set(config.redis.access_token_key, tokens.access_token, ex=ttl)
            return tokens.access_token

        # 4. Обновляем токен
        new_tokens = await self._refresh_tokens(tokens.refresh_token)
        return new_tokens["access_token"]

    async def _request_authorization(self):
        """Отправляет запрос на авторизацию администратору"""
        # Импортируем bot только когда он нужен, чтобы избежать циклических импортов
        from src.bot_init import bot

        await bot.send_message(
            config.bot.admin_id,
            f"Требуется авторизация в hh.ru\n"
            f"Пожалуйста, перейдите по ссылке: {config.hh.auth_url}"
        )

    async def _refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        """Обновляет токены через refresh_token"""
        from src.models import HHToken

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": config.hh.client_id.get_secret_value(),
            "client_secret": config.hh.client_secret.get_secret_value(),
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(config.hh.token_url, data=data)
            if response.status_code != 200:
                raise Exception(f"Не удалось обновить токены: {response.text}")

            tokens_data = response.json()
            access_token = tokens_data.get("access_token")
            new_refresh_token = tokens_data.get("refresh_token", refresh_token)
            expires_in = tokens_data.get("expires_in", 3600)
            expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=expires_in)

            # Сохраняем в базу
            tokens = await HHToken.get(id=1)
            tokens.access_token = access_token
            tokens.refresh_token = new_refresh_token
            tokens.expires_at = expires_at
            await tokens.save()

            # Сохраняем в Redis
            await redis.set(config.redis.access_token_key, access_token, ex=expires_in)

            return {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "expires_in": expires_in
            }

    async def get_headers(self) -> Dict[str, str]:
        """
        Возвращает заголовки для запросов к API HH

        Returns:
            Dict[str, str]: Заголовки запроса
        """
        access_token = await self.get_access_token()
        return {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "HH-Job-Bot (CodeGPT)"
        }

    async def get_resume(self, resume_id: str) -> Dict[str, Any]:
        """
        Получает резюме по ID

        Args:
            resume_id: ID резюме

        Returns:
            Dict[str, Any]: Данные резюме
        """
        url = f"{config.hh.resume_url}{resume_id}"
        headers = await self.get_headers()

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def get_vacancy(self, vacancy_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает данные о вакансии по её ID

        Args:
            vacancy_id: ID вакансии

        Returns:
            Dict[str, Any]: Данные вакансии или None в случае ошибки
        """
        url = f"https://api.hh.ru/vacancies/{vacancy_id}"
        headers = await self.get_headers()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Ошибка HTTP: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            print(f"Ошибка запроса: {e}")
            return None

    async def search_similar_vacancies(self, text: str, resume_id: str, per_page: int = 10) -> list:
        """
        Ищет похожие вакансии для резюме

        Args:
            text: Текст для поиска
            resume_id: ID резюме
            per_page: Количество результатов на странице

        Returns:
            list: Список вакансий
        """
        url = f"https://api.hh.ru/resumes/{resume_id}/similar_vacancies"

        params = {
            "text": text,
            "search_field": "name",
            "salary": 140000,
            "currency": "RUR",
            "schedule": "remote",
            "per_page": per_page,
            "page": 0,
            "order_by": "relevance"
        }

        headers = await self.get_headers()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                return data.get("items", [])
        except httpx.HTTPStatusError as e:
            print(f"Ошибка HTTP: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            print(f"Ошибка при выполнении запроса: {e}")
            return []

    async def apply_to_vacancy(self, resume_id: str, vacancy_id: str, message: str) -> bool:
        """
        Откликается на вакансию

        Args:
            resume_id: ID резюме
            vacancy_id: ID вакансии
            message: Сопроводительное письмо

        Returns:
            bool: True если отклик успешно отправлен
        """
        url = "https://api.hh.ru/negotiations"
        headers = await self.get_headers()
        data = {
            "vacancy_id": vacancy_id,
            "resume_id": resume_id,
            "message": message
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, data=data)
                response.raise_for_status()
                return True
        except httpx.HTTPStatusError as e:
            print(f"Ошибка HTTP при отклике на {vacancy_id}: {e.response.status_code} - {e.response.text}")
            return False
        except httpx.RequestError as e:
            print(f"Ошибка запроса при отклике на {vacancy_id}: {e}")
            return False
        except Exception as e:
            print(f"Неожиданная ошибка при отклике на {vacancy_id}: {e}")
            return False

    async def get_employment_dictionaries(self) -> Optional[Dict[str, Any]]:
        """
        Получает словари для работы с API (типы занятости и т.д.)

        Returns:
            Dict[str, Any]: Словари или None в случае ошибки
        """
        url = "https://api.hh.ru/dictionaries"
        headers = await self.get_headers()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Ошибка HTTP: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            print(f"Ошибка запроса: {e}")
            return None

    @staticmethod
    def extract_job_description_from_vacancy(vacancy_data: Dict[str, Any]) -> str:
        """
        Извлекает описание вакансии из JSON-ответа HeadHunter API

        Args:
            vacancy_data: JSON-ответ от API HeadHunter

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

# Создаем единственный экземпляр клиента
hh_client = HHAPIClient()