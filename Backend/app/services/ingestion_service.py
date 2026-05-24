import csv
import io
import json
import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.event import Event
from app.repositories.event_repository import EventRepository
from app.schemas.event import EventCreate
from app.utils.rate_limit import RateLimiter


class IngestionService:
    QUEUE_KEY = "ingest:events"

    def __init__(self, session: AsyncSession, redis_client: aioredis.Redis) -> None:
        self.session = session
        self.redis = redis_client
        self.event_repo = EventRepository(session)
        self.rate_limiter = RateLimiter(redis_client)
        self.settings = get_settings()

    def normalize_event(
        self, organization_id: UUID, data: EventCreate, source: str = "api"
    ) -> dict[str, Any]:
        occurred = data.occurred_at or datetime.now(timezone.utc)
        if occurred.tzinfo is None:
            occurred = occurred.replace(tzinfo=timezone.utc)
        return {
            "organization_id": str(organization_id),
            "event_name": data.event_name,
            "occurred_at": occurred.isoformat(),
            "received_at": datetime.now(timezone.utc).isoformat(),
            "properties": data.properties,
            "user_id": data.user_id,
            "session_id": data.session_id,
            "source": source,
        }

    async def enqueue_event(
        self, organization_id: UUID, data: EventCreate, source: str = "api"
    ) -> UUID:
        await self.rate_limiter.check_org_ingest_limit(str(organization_id))
        ingest_id = uuid.uuid4()
        payload = self.normalize_event(organization_id, data, source)
        payload["ingest_id"] = str(ingest_id)
        await self.redis.lpush(self.QUEUE_KEY, json.dumps(payload))
        return ingest_id

    async def enqueue_batch(
        self, organization_id: UUID, events: list[EventCreate], source: str = "api"
    ) -> UUID:
        await self.rate_limiter.check_org_ingest_limit(str(organization_id))
        ingest_id = uuid.uuid4()
        pipe = self.redis.pipeline()
        for event in events:
            payload = self.normalize_event(organization_id, event, source)
            payload["ingest_id"] = str(ingest_id)
            pipe.lpush(self.QUEUE_KEY, json.dumps(payload))
        await pipe.execute()
        return ingest_id

    async def enqueue_csv(
        self, organization_id: UUID, file_content: bytes
    ) -> tuple[UUID, int]:
        content = file_content.decode("utf-8")
        row_count = len(self.parse_csv(content))
        ingest_id = uuid.uuid4()
        await self.redis.lpush(
            "ingest:csv",
            json.dumps({
                "organization_id": str(organization_id),
                "ingest_id": str(ingest_id),
                "content": content,
            }),
        )
        return ingest_id, row_count

    @staticmethod
    def payloads_to_models(payloads: list[dict]) -> list[Event]:
        events = []
        for p in payloads:
            events.append(
                Event(
                    organization_id=UUID(p["organization_id"]),
                    event_name=p["event_name"],
                    occurred_at=datetime.fromisoformat(p["occurred_at"]),
                    received_at=datetime.fromisoformat(p["received_at"]),
                    properties=p.get("properties", {}),
                    user_id=p.get("user_id"),
                    session_id=p.get("session_id"),
                    source=p.get("source", "api"),
                    ingest_id=UUID(p["ingest_id"]) if p.get("ingest_id") else None,
                )
            )
        return events

    async def persist_batch(self, payloads: list[dict]) -> int:
        if not payloads:
            return 0
        events = self.payloads_to_models(payloads)
        count = await self.event_repo.bulk_create(events)
        org_id = payloads[0]["organization_id"]
        stream_events = [
            {
                "event_name": p["event_name"],
                "occurred_at": p["occurred_at"],
                "properties": p.get("properties", {}),
                "user_id": p.get("user_id"),
                "source": p.get("source", "api"),
            }
            for p in payloads[:50]
        ]
        await self.redis.publish(
            f"org:{org_id}:events",
            json.dumps({
                "type": "event.ingested",
                "count": count,
                "events": stream_events,
            }),
        )
        await self.redis.publish(
            f"org:{org_id}:dashboard",
            json.dumps({"type": "dashboard.refresh"}),
        )
        return count

    @staticmethod
    def parse_csv(content: str) -> list[dict]:
        reader = csv.DictReader(io.StringIO(content))
        rows = []
        for row in reader:
            event_name = row.get("event_name") or row.get("event")
            if not event_name:
                continue
            occurred = row.get("occurred_at") or datetime.now(timezone.utc).isoformat()
            properties = {
                k: v for k, v in row.items()
                if k not in ("event_name", "event", "occurred_at", "user_id", "session_id")
            }
            rows.append({
                "event_name": event_name.strip().lower().replace(" ", "_"),
                "occurred_at": occurred,
                "properties": properties,
                "user_id": row.get("user_id"),
                "session_id": row.get("session_id"),
                "source": "csv",
            })
        return rows
