# src/handlers/bot/__init__.py
from .start import router as start_router
from .add_resume import router as add_resume_router
from .admin import router as admin_router

routers = [start_router, admin_router, add_resume_router]
