from .add_resume import router as add_resume_router
from .list_resumes import router as list_resumes_router
from .manage_resume import router as manage_resume_router
from .keywords import router as keywords_router

resume_routers = [
    add_resume_router,
    list_resumes_router,
    manage_resume_router,
    keywords_router,
]
