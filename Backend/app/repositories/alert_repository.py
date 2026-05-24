from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.alert import AlertIncident, AlertRule, InAppNotification
from app.repositories.base import BaseRepository
from app.utils.pagination import PaginatedResult, PaginationParams


class AlertRuleRepository(BaseRepository[AlertRule]):
    model = AlertRule

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_by_org(
        self, organization_id: UUID, params: PaginationParams
    ) -> PaginatedResult[AlertRule]:
        base = select(AlertRule).where(AlertRule.organization_id == organization_id)
        base = self._active(base)
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()
        stmt = base.order_by(AlertRule.created_at.desc()).offset(params.skip).limit(params.limit)
        items = list((await self.session.execute(stmt)).scalars().all())
        return PaginatedResult(items=items, total=total, page=params.page, page_size=params.page_size)

    async def list_evaluable(self) -> list[AlertRule]:
        now = datetime.now(timezone.utc)
        stmt = self._active(select(AlertRule)).where(
            AlertRule.status.in_(["active", "triggered"]),
            (AlertRule.muted_until.is_(None)) | (AlertRule.muted_until < now),
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_for_org(self, rule_id: UUID, organization_id: UUID) -> AlertRule | None:
        stmt = self._active(
            select(AlertRule).where(
                AlertRule.id == rule_id,
                AlertRule.organization_id == organization_id,
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()


class AlertIncidentRepository(BaseRepository[AlertIncident]):
    model = AlertIncident

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_by_rule(
        self, alert_rule_id: UUID, params: PaginationParams
    ) -> PaginatedResult[AlertIncident]:
        base = select(AlertIncident).where(AlertIncident.alert_rule_id == alert_rule_id)
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()
        stmt = (
            base.order_by(AlertIncident.triggered_at.desc())
            .offset(params.skip)
            .limit(params.limit)
        )
        items = list((await self.session.execute(stmt)).scalars().all())
        return PaginatedResult(items=items, total=total, page=params.page, page_size=params.page_size)

    async def get_open_for_rule(self, alert_rule_id: UUID) -> AlertIncident | None:
        stmt = select(AlertIncident).where(
            AlertIncident.alert_rule_id == alert_rule_id,
            AlertIncident.status == "triggered",
            AlertIncident.resolved_at.is_(None),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()


class NotificationRepository(BaseRepository[InAppNotification]):
    model = InAppNotification

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_for_org(
        self, organization_id: UUID, user_id: UUID | None, params: PaginationParams
    ) -> PaginatedResult[InAppNotification]:
        base = select(InAppNotification).where(InAppNotification.organization_id == organization_id)
        if user_id:
            base = base.where(
                (InAppNotification.user_id.is_(None)) | (InAppNotification.user_id == user_id)
            )
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()
        stmt = base.order_by(InAppNotification.created_at.desc()).offset(params.skip).limit(params.limit)
        items = list((await self.session.execute(stmt)).scalars().all())
        return PaginatedResult(items=items, total=total, page=params.page, page_size=params.page_size)

    async def mark_read(self, notification_id: UUID, organization_id: UUID) -> InAppNotification | None:
        stmt = select(InAppNotification).where(
            InAppNotification.id == notification_id,
            InAppNotification.organization_id == organization_id,
        )
        notif = (await self.session.execute(stmt)).scalar_one_or_none()
        if notif and not notif.read_at:
            notif.read_at = datetime.now(timezone.utc)
            await self.session.flush()
        return notif
