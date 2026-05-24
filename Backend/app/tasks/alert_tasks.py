import asyncio
import json

import redis
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.services.alert_service import AlertService
from app.tasks.celery_app import celery_app


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _evaluate_alerts() -> dict:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        async with session_factory() as session:
            service = AlertService(session, redis_client)
            count = await service.evaluate_all()
            await session.commit()
        return {"evaluated": count}
    finally:
        await redis_client.aclose()
        await engine.dispose()


@celery_app.task(name="app.tasks.alert_tasks.evaluate_alerts")
def evaluate_alerts() -> dict:
    return _run_async(_evaluate_alerts())
