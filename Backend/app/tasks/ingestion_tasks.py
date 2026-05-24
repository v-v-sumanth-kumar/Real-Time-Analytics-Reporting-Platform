import asyncio
import json
from datetime import datetime, timezone
from uuid import UUID

import redis
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.repositories.event_repository import EventRepository
from app.services.ingestion_service import IngestionService
from app.tasks.celery_app import celery_app

settings = get_settings()

BATCH_SIZE = 500


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _process_event_queue(batch_size: int = BATCH_SIZE) -> int:
    r_sync = redis.from_url(settings.redis_url, decode_responses=True)
    payloads = []
    try:
        for _ in range(batch_size):
            raw = r_sync.rpop(IngestionService.QUEUE_KEY)
            if not raw:
                break
            payloads.append(json.loads(raw))
    finally:
        r_sync.close()

    if not payloads:
        return 0

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)

    try:
        async with session_factory() as session:
            service = IngestionService(session, redis_client)
            count = await service.persist_batch(payloads)
            await session.commit()
        return count
    finally:
        await redis_client.aclose()
        await engine.dispose()


@celery_app.task(name="app.tasks.ingestion_tasks.process_ingest_queue")
def process_ingest_queue() -> dict:
    count = _run_async(_process_event_queue())
    return {"processed": count}


async def _process_csv_queue() -> int:
    r = redis.from_url(settings.redis_url, decode_responses=True)
    raw = r.rpop("ingest:csv")
    if not raw:
        return 0

    job = json.loads(raw)
    rows = IngestionService.parse_csv(job["content"])

    org_id = UUID(job["organization_id"])
    ingest_id = job.get("ingest_id")

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        async with session_factory() as session:
            service = IngestionService(session, redis_client)
            payloads = []
            for row in rows:
                from app.schemas.event import EventCreate
                from datetime import datetime as dt

                occurred = row.get("occurred_at")
                if isinstance(occurred, str):
                    try:
                        occurred_dt = dt.fromisoformat(occurred.replace("Z", "+00:00"))
                    except ValueError:
                        occurred_dt = datetime.now(timezone.utc)
                else:
                    occurred_dt = datetime.now(timezone.utc)

                event = EventCreate(
                    event_name=row["event_name"],
                    occurred_at=occurred_dt,
                    properties=row.get("properties", {}),
                    user_id=row.get("user_id"),
                    session_id=row.get("session_id"),
                )
                p = service.normalize_event(org_id, event, source="csv")
                p["ingest_id"] = ingest_id
                payloads.append(p)

            if payloads:
                events = IngestionService.payloads_to_models(payloads)
                repo = EventRepository(session)
                count = await repo.bulk_create(events)
                await session.commit()
                await redis_client.publish(
                    f"org:{org_id}:events",
                    json.dumps({
                        "type": "event.ingested",
                        "count": count,
                        "events": [
                            {
                                "id": str(e.id),
                                "event_name": e.event_name,
                                "occurred_at": e.occurred_at.isoformat(),
                                "properties": e.properties or {},
                                "user_id": e.user_id,
                                "source": e.source,
                            }
                            for e in events[:50]
                        ],
                    }),
                )
                await redis_client.publish(
                    f"org:{org_id}:dashboard",
                    json.dumps({"type": "dashboard.refresh"}),
                )
            else:
                count = 0
        return count
    finally:
        await redis_client.aclose()
        await engine.dispose()


@celery_app.task(name="app.tasks.ingestion_tasks.process_csv_queue")
def process_csv_queue() -> dict:
    count = _run_async(_process_csv_queue())
    return {"processed": count}


@celery_app.task(name="app.tasks.ingestion_tasks.cleanup_expired_invitations")
def cleanup_expired_invitations() -> dict:
    async def _cleanup() -> int:
        from datetime import datetime, timezone
        from sqlalchemy import delete
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from app.core.config import get_settings
        from app.models.invitation import Invitation

        settings = get_settings()
        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        try:
            async with session_factory() as session:
                now = datetime.now(timezone.utc)
                stmt = delete(Invitation).where(
                    Invitation.accepted_at.is_(None),
                    Invitation.expires_at < now,
                )
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount or 0
        finally:
            await engine.dispose()

    deleted = _run_async(_cleanup())
    return {"deleted": deleted}


# Periodic drain — Celery Beat can call every few seconds
@celery_app.task(name="app.tasks.ingestion_tasks.drain_ingest_queue")
def drain_ingest_queue() -> dict:
    total = 0
    for _ in range(10):
        count = _run_async(_process_event_queue())
        total += count
        if count == 0:
            break
    csv_count = _run_async(_process_csv_queue())
    return {"events_processed": total, "csv_processed": csv_count}
