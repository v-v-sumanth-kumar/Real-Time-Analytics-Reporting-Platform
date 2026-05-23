from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.dashboard import Dashboard
from app.models.widget import Widget
from app.repositories.base import BaseRepository
from app.utils.pagination import PaginatedResult, PaginationParams


class DashboardRepository(BaseRepository[Dashboard]):
    model = Dashboard

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(self, **kwargs) -> Dashboard:
        dashboard = Dashboard(**kwargs)
        self.session.add(dashboard)
        await self.session.flush()
        return dashboard

    async def get_with_widgets(self, dashboard_id: UUID) -> Dashboard | None:
        stmt = (
            self._active(
                select(Dashboard)
                .where(Dashboard.id == dashboard_id)
                .options(selectinload(Dashboard.widgets))
            )
        )
        result = await self.session.execute(stmt)
        dashboard = result.scalar_one_or_none()
        if dashboard:
            dashboard.widgets = [w for w in dashboard.widgets if w.deleted_at is None]
        return dashboard

    async def list_by_org(
        self, organization_id: UUID, params: PaginationParams
    ) -> PaginatedResult[Dashboard]:
        base = self._active(
            select(Dashboard).where(Dashboard.organization_id == organization_id)
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            base.options(selectinload(Dashboard.widgets))
            .order_by(Dashboard.created_at.desc())
            .offset(params.skip)
            .limit(params.limit)
        )
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())
        for d in items:
            d.widgets = [w for w in d.widgets if w.deleted_at is None]
        return PaginatedResult(
            items=items, total=total, page=params.page, page_size=params.page_size
        )

    async def get_by_share_token_hash(self, token_hash: str) -> Dashboard | None:
        stmt = (
            select(Dashboard)
            .where(
                Dashboard.share_token_hash == token_hash,
                Dashboard.is_public.is_(True),
                Dashboard.deleted_at.is_(None),
            )
            .options(selectinload(Dashboard.widgets))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class WidgetRepository(BaseRepository[Widget]):
    model = Widget

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(self, **kwargs) -> Widget:
        widget = Widget(**kwargs)
        self.session.add(widget)
        await self.session.flush()
        return widget

    async def get_by_id_for_org(self, widget_id: UUID, organization_id: UUID) -> Widget | None:
        stmt = self._active(
            select(Widget).where(
                Widget.id == widget_id,
                Widget.organization_id == organization_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
