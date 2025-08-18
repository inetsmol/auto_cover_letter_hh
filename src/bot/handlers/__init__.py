# src/bot/handlers/__init__.py
from .start import router as start_router
from .common import router as common_router
from .notifications import router as notification_router
from .admin.task_management import router as admin_task_management_router
from .fallback import router as fallback_router

routers = [start_router, common_router, notification_router, admin_task_management_router] + [fallback_router]
