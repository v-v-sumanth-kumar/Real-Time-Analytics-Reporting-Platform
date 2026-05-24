from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.repositories.base import BaseRepository
from app.utils.pagination import PaginatedResult, PaginationParams


class EventRepository(BaseRepository[Event]):
    model = Event

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def bulk_create(self, events: list[Event]) -> int:
        self.session.add_all(events)
        await self.session.flush()
        return len(events)

    async def list_by_org(
        self, organization_id: UUID, params: PaginationParams
    ) -> PaginatedResult[Event]:
        base = select(Event).where(Event.organization_id == organization_id)
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            base.order_by(Event.occurred_at.desc())
            .offset(params.skip)
            .limit(params.limit)
        )
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())
        return PaginatedResult(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    @staticmethod
    def parse_time_range(time_range: str) -> tuple[datetime, datetime]:
        now = datetime.now(timezone.utc)
        mapping = {
            "1h": timedelta(hours=1),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "90d": timedelta(days=90),
        }
        delta = mapping.get(time_range, timedelta(hours=24))
        return now - delta, now

    async def aggregate_count(
        self,
        organization_id: UUID,
        event_name: str | None,
        start: datetime,
        end: datetime,
        group_by: str | None = None,
        granularity: str = "1h",
    ) -> list[dict]:
        trunc = {
            "1h": "hour",
            "1d": "day",
            "1w": "week",
        }.get(granularity, "hour")

        if group_by:
            # group_by format: properties.country
            if group_by.startswith("properties."):
                field = group_by.split(".", 1)[1]
                group_expr = Event.properties[field].astext
            else:
                group_expr = getattr(Event, group_by, Event.event_name)

            stmt = (
                select(
                    func.date_trunc(trunc, Event.occurred_at).label("bucket"),
                    group_expr.label("label"),
                    func.count().label("value"),
                )
                .where(
                    Event.organization_id == organization_id,
                    Event.occurred_at >= start,
                    Event.occurred_at < end,
                )
                .group_by(text("bucket"), group_expr)
                .order_by(text("bucket"))
            )
            if event_name:
                stmt = stmt.where(Event.event_name == event_name)
        else:
            stmt = (
                select(
                    func.date_trunc(trunc, Event.occurred_at).label("bucket"),
                    func.count().label("value"),
                )
                .where(
                    Event.organization_id == organization_id,
                    Event.occurred_at >= start,
                    Event.occurred_at < end,
                )
                .group_by(text("bucket"))
                .order_by(text("bucket"))
            )
            if event_name:
                stmt = stmt.where(Event.event_name == event_name)

        result = await self.session.execute(stmt)
        rows = result.all()
        data = []
        for row in rows:
            if group_by:
                data.append({
                    "timestamp": row.bucket.isoformat() if row.bucket else None,
                    "label": str(row.label) if row.label else "unknown",
                    "value": float(row.value),
                })
            else:
                data.append({
                    "timestamp": row.bucket.isoformat() if row.bucket else None,
                    "label": "count",
                    "value": float(row.value),
                })
        return data

    async def aggregate_total(
        self,
        organization_id: UUID,
        event_name: str | None,
        start: datetime,
        end: datetime,
    ) -> float:
        stmt = select(func.count()).where(
            Event.organization_id == organization_id,
            Event.occurred_at >= start,
            Event.occurred_at < end,
        )
        if event_name:
            stmt = stmt.where(Event.event_name == event_name)
        result = await self.session.execute(stmt)
        return float(result.scalar_one())
