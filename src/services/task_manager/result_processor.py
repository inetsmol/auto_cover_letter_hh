# src/services/task_manager/result_processor.py

from __future__ import annotations

from typing import Optional

from src.models import TaskResult, RunType


async def save_run_result(
    *,
    user_id: int,
    run_type: str,
    resumes_enqueued: int,
    meta: Optional[dict] = None,
) -> TaskResult:
    """
    Сохраняем результат пробега для пользователя.
    run_type: 'free_daily' | 'paid_hourly' | 'bulk' | 'manual'
    """
    # нормализуем значение в Enum (если придёт строка)
    rt = RunType(run_type) if run_type in RunType.__members__.values() or run_type in RunType._value2member_map_ else {
        "free_daily": RunType.FREE_DAILY,
        "paid_hourly": RunType.PAID_HOURLY,
        "bulk": RunType.BULK,
        "manual": RunType.MANUAL,
    }.get(run_type, RunType.MANUAL)

    obj = await TaskResult.create(
        user_id=user_id,
        run_type=rt,
        resumes_enqueued=int(resumes_enqueued or 0),
        meta=meta or {},
    )
    return obj
