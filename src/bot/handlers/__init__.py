# src/bot/handlers/__init__.py
from .start import router as start_router
from .admin.task_management import router as admin_task_management_router

from .resume import resume_routers

routers = [start_router, admin_task_management_router] + resume_routers
