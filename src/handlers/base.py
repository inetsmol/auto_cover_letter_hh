# src/handlers/base.py
from fastapi import APIRouter
from starlette.responses import PlainTextResponse

base_router = APIRouter()

@base_router.get("/health")
async def health():
    return PlainTextResponse("OK")
