# src/services/startup.py
from src.db.init import init_db
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = None

async def on_startup():
    global scheduler
    await init_db()
    scheduler = AsyncIOScheduler()
    scheduler.start()

async def on_shutdown():
    global scheduler
    if scheduler:
        scheduler.shutdown()
