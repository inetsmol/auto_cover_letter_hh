# src/workers/init.py

# Позволяет autodiscover подхватить таски
from .application_sender_worker import (  # noqa: F401
    schedule_bulk_apply,
    apply_for_resume,
    apply_for_vacancy,
)
