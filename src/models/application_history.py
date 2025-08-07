# src/models/application_history.py
from tortoise.models import Model
from tortoise import fields
from datetime import datetime
from typing import Dict, Any, Optional


class VacancySnapshot(Model):
    """Снимок вакансии на момент отклика"""

    class Meta:
        table = "vacancy_snapshots"

    id = fields.IntField(pk=True)
    vacancy_id = fields.CharField(max_length=50, unique=True)  # HH vacancy ID

    # Основная информация
    title = fields.CharField(max_length=300)
    company_name = fields.CharField(max_length=200, null=True)
    company_id = fields.CharField(max_length=50, null=True)

    # Зарплата
    salary_from = fields.IntField(null=True)
    salary_to = fields.IntField(null=True)
    salary_currency = fields.CharField(max_length=10, default='RUR')

    # Местоположение
    area_name = fields.CharField(max_length=100, null=True)
    address = fields.TextField(null=True)
    metro_stations = fields.JSONField(default=list)

    # Требования
    experience_name = fields.CharField(max_length=100, null=True)
    employment_name = fields.CharField(max_length=100, null=True)
    schedule_name = fields.CharField(max_length=100, null=True)

    # Содержимое
    description = fields.TextField(null=True)
    key_skills = fields.JSONField(default=list)
    languages = fields.JSONField(default=list)

    # Дополнительная информация
    has_test = fields.BooleanField(default=False)
    premium = fields.BooleanField(default=False)
    archived = fields.BooleanField(default=False)

    # Полный JSON от HH API
    full_data = fields.JSONField(default=dict)

    # Даты
    published_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class ApplicationHistory(Model):
    """История откликов на вакансии"""

    class Meta:
        table = "application_history"
        ordering = ["-applied_at"]
        # Уникальность по комбинации resume_id + vacancy_id
        unique_together = [("resume_id", "vacancy_id")]

    APPLICATION_STATUS_CHOICES = [
        ('sent', 'Sent'),  # Отправлено
        ('viewed', 'Viewed'),  # Просмотрено работодателем
        ('declined', 'Declined'),  # Отклонено
        ('invitation', 'Invitation'),  # Приглашение на интервью
        ('discard', 'Discard'),  # Отклонено кандидатом
        ('response', 'Response'),  # Ответ от работодателя
        ('failed', 'Failed'),  # Ошибка отправки
    ]

    APPLICATION_SOURCE_CHOICES = [
        ('manual', 'Manual'),  # Ручная отправка через бота
        ('scheduled', 'Scheduled'),  # Автоматическая по расписанию
        ('batch', 'Batch'),  # Массовая обработка
        ('retry', 'Retry'),  # Повторная попытка
        ('admin', 'Admin'),  # Отправлено админом
    ]

    id = fields.IntField(pk=True)

    # Связи
    resume = fields.ForeignKeyField(
        "models.Resume",
        related_name="applications",
        on_delete=fields.CASCADE
    )
    resume_id = fields.CharField(max_length=50)  # Дублируем для удобства запросов

    vacancy = fields.ForeignKeyField(
        "VacancySnapshot",
        related_name="applications",
        on_delete=fields.CASCADE
    )
    vacancy_id = fields.CharField(max_length=50)  # HH vacancy ID

    # Связь с выполнением задачи
    job_execution = fields.ForeignKeyField(
        "models.JobExecutionResult",
        related_name="applications",
        null=True,
        on_delete=fields.SET_NULL
    )

    # Статус и источник
    status = fields.CharField(max_length=30, choices=APPLICATION_STATUS_CHOICES, default='sent')
    source = fields.CharField(max_length=30, choices=APPLICATION_SOURCE_CHOICES, default='manual')

    # Содержимое отклика
    cover_letter = fields.TextField()  # Сопроводительное письмо
    cover_letter_hash = fields.CharField(max_length=64, null=True)  # MD5 для дедупликации

    # Время
    applied_at = fields.DatetimeField(auto_now_add=True)
    status_updated_at = fields.DatetimeField(auto_now=True)

    # Результат отправки
    hh_response = fields.JSONField(default=dict)  # Ответ от HH API
    hh_negotiation_id = fields.CharField(max_length=50, null=True)  # ID переговоров в HH

    # Ошибки
    error_message = fields.TextField(null=True)
    retry_count = fields.IntField(default=0)

    # Дополнительная информация
    user_agent = fields.CharField(max_length=255, null=True)  # User-Agent при отправке
    ip_address = fields.CharField(max_length=45, null=True)  # IP адрес (для отладки)

    @property
    def is_successful(self) -> bool:
        """Проверяет, был ли отклик успешно отправлен"""
        return self.status in ['sent', 'viewed', 'invitation', 'response']

    @property
    def is_pending_response(self) -> bool:
        """Проверяет, ожидает ли отклик ответа от работодателя"""
        return self.status in ['sent', 'viewed']

    async def update_status(self, new_status: str, hh_data: Dict = None):
        """Обновляет статус отклика"""
        self.status = new_status
        self.status_updated_at = datetime.utcnow()
        if hh_data:
            self.hh_response.update(hh_data)
        await self.save()

    async def mark_as_failed(self, error_message: str):
        """Отмечает отклик как неудачный"""
        self.status = 'failed'
        self.error_message = error_message
        self.retry_count += 1
        self.status_updated_at = datetime.utcnow()
        await self.save()

    def get_summary(self) -> Dict[str, Any]:
        """Возвращает краткую информацию об отклике"""
        return {
            'id': self.id,
            'resume_id': self.resume_id,
            'vacancy_id': self.vacancy_id,
            'status': self.status,
            'source': self.source,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'is_successful': self.is_successful,
            'retry_count': self.retry_count,
        }


class ApplicationStatistics(Model):
    """Агрегированная статистика по откликам"""

    class Meta:
        table = "application_statistics"

    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    id = fields.IntField(pk=True)

    # Период
    period_type = fields.CharField(max_length=20, choices=PERIOD_CHOICES)
    period_start = fields.DateField()
    period_end = fields.DateField()

    # Пользователь (null для общей статистики)
    user = fields.ForeignKeyField(
        "models.User",
        related_name="application_stats",
        null=True,
        on_delete=fields.CASCADE
    )

    # Резюме (null для статистики по всем резюме пользователя)
    resume = fields.ForeignKeyField(
        "models.Resume",
        related_name="application_stats",
        null=True,
        on_delete=fields.CASCADE
    )

    # Статистика
    total_applications = fields.IntField(default=0)
    successful_applications = fields.IntField(default=0)
    failed_applications = fields.IntField(default=0)
    viewed_applications = fields.IntField(default=0)
    invitations_received = fields.IntField(default=0)

    # Уникальные метрики
    unique_companies_contacted = fields.IntField(default=0)
    unique_vacancies_applied = fields.IntField(default=0)

    # Средние значения
    avg_applications_per_day = fields.FloatField(default=0.0)
    avg_success_rate = fields.FloatField(default=0.0)
    avg_response_time_hours = fields.FloatField(null=True)  # Среднее время ответа

    # Топ категории/навыки/компании
    top_companies = fields.JSONField(default=list)  # [{company, count}, ...]
    top_skills = fields.JSONField(default=list)  # [{skill, count}, ...]
    top_locations = fields.JSONField(default=list)  # [{location, count}, ...]

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    @property
    def success_rate(self) -> float:
        """Процент успешных откликов"""
        if self.total_applications == 0:
            return 0.0
        return (self.successful_applications / self.total_applications) * 100

    @property
    def invitation_rate(self) -> float:
        """Процент приглашений от общего количества откликов"""
        if self.total_applications == 0:
            return 0.0
        return (self.invitations_received / self.total_applications) * 100

    def get_summary(self) -> Dict[str, Any]:
        """Возвращает сводку статистики"""
        return {
            'period': f"{self.period_start} - {self.period_end}",
            'period_type': self.period_type,
            'total_applications': self.total_applications,
            'successful_applications': self.successful_applications,
            'success_rate': round(self.success_rate, 1),
            'invitations_received': self.invitations_received,
            'invitation_rate': round(self.invitation_rate, 1),
            'unique_companies': self.unique_companies_contacted,
            'avg_per_day': round(self.avg_applications_per_day, 1),
        }