from typing import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import attributes

from app.core.exceptions import NotFoundError
from app.models.widget import Widget
from app.core.security import generate_share_token
from app.repositories.dashboard_repository import DashboardRepository, WidgetRepository
from app.repositories.event_repository import EventRepository
from app.schemas.dashboard import (
    DashboardCreate,
    DashboardResponse,
    DashboardUpdate,
    MetricDataPoint,
    WidgetCreate,
    WidgetMetricsResponse,
    WidgetResponse,
    WidgetUpdate,
)
from app.utils.pagination import PaginatedResult, PaginationParams


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.dashboard_repo = DashboardRepository(session)
        self.widget_repo = WidgetRepository(session)
        self.event_repo = EventRepository(session)

    def _loaded_widgets(self, dashboard) -> list[Widget]:
        """Read widgets only when eager-loaded; never trigger async lazy load."""
        state = attributes.instance_state(dashboard)
        if "widgets" in state.unloaded:
            return []
        return [w for w in dashboard.widgets if w.deleted_at is None]

    def _dashboard_response(
        self,
        dashboard,
        *,
        widgets: Sequence[Widget] | None = None,
    ) -> DashboardResponse:
        active = list(widgets) if widgets is not None else self._loaded_widgets(dashboard)
        widget_responses = [WidgetResponse.model_validate(w) for w in active]
        return DashboardResponse(
            id=dashboard.id,
            organization_id=dashboard.organization_id,
            name=dashboard.name,
            description=dashboard.description,
            layout=dashboard.layout,
            is_public=dashboard.is_public,
            refresh_interval_sec=dashboard.refresh_interval_sec,
            widgets=widget_responses,
            created_at=dashboard.created_at,
        )

    async def create(
        self, organization_id: UUID, user_id: UUID, data: DashboardCreate
    ) -> DashboardResponse:
        dashboard = await self.dashboard_repo.create(
            organization_id=organization_id,
            name=data.name,
            description=data.description,
            layout=data.layout,
            refresh_interval_sec=data.refresh_interval_sec,
            created_by=user_id,
        )
        return self._dashboard_response(dashboard, widgets=[])

    async def list(
        self, organization_id: UUID, params: PaginationParams
    ) -> PaginatedResult[DashboardResponse]:
        result = await self.dashboard_repo.list_by_org(organization_id, params)
        return PaginatedResult(
            items=[self._dashboard_response(d) for d in result.items],
            total=result.total,
            page=result.page,
            page_size=result.page_size,
        )

    async def get(self, organization_id: UUID, dashboard_id: UUID) -> DashboardResponse:
        dashboard = await self.dashboard_repo.get_with_widgets(dashboard_id)
        if not dashboard or dashboard.organization_id != organization_id:
            raise NotFoundError("Dashboard not found")
        return self._dashboard_response(dashboard)

    async def update(
        self, organization_id: UUID, dashboard_id: UUID, data: DashboardUpdate
    ) -> DashboardResponse:
        dashboard = await self.dashboard_repo.get_with_widgets(dashboard_id)
        if not dashboard or dashboard.organization_id != organization_id:
            raise NotFoundError("Dashboard not found")

        updates = data.model_dump(exclude_unset=True)
        if "is_public" in updates and updates["is_public"] and not dashboard.share_token_hash:
            _, token_hash = generate_share_token()
            dashboard.share_token_hash = token_hash
        for key, value in updates.items():
            setattr(dashboard, key, value)
        await self.session.flush()
        return self._dashboard_response(dashboard)

    async def delete(self, organization_id: UUID, dashboard_id: UUID) -> None:
        dashboard = await self.dashboard_repo.get_by_id(dashboard_id)
        if not dashboard or dashboard.organization_id != organization_id:
            raise NotFoundError("Dashboard not found")
        await self.dashboard_repo.soft_delete(dashboard)

    async def get_public(self, share_token: str) -> DashboardResponse:
        import hashlib
        token_hash = hashlib.sha256(share_token.encode()).hexdigest()
        dashboard = await self.dashboard_repo.get_by_share_token_hash(token_hash)
        if not dashboard:
            raise NotFoundError("Dashboard not found or not shared")
        return self._dashboard_response(dashboard)

    async def add_widget(
        self,
        organization_id: UUID,
        dashboard_id: UUID,
        data: WidgetCreate,
    ) -> WidgetResponse:
        dashboard = await self.dashboard_repo.get_by_id(dashboard_id)
        if not dashboard or dashboard.organization_id != organization_id:
            raise NotFoundError("Dashboard not found")

        query = data.query.model_dump() if hasattr(data.query, "model_dump") else data.query
        widget = await self.widget_repo.create(
            dashboard_id=dashboard_id,
            organization_id=organization_id,
            type=data.type,
            title=data.title,
            config=data.config,
            query=query,
            position=data.position,
            refresh_interval_sec=data.refresh_interval_sec,
        )
        return WidgetResponse.model_validate(widget)

    async def update_widget(
        self,
        organization_id: UUID,
        widget_id: UUID,
        data: WidgetUpdate,
    ) -> WidgetResponse:
        widget = await self.widget_repo.get_by_id_for_org(widget_id, organization_id)
        if not widget:
            raise NotFoundError("Widget not found")
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(widget, key, value)
        await self.session.flush()
        return WidgetResponse.model_validate(widget)

    async def delete_widget(self, organization_id: UUID, widget_id: UUID) -> None:
        widget = await self.widget_repo.get_by_id_for_org(widget_id, organization_id)
        if not widget:
            raise NotFoundError("Widget not found")
        await self.widget_repo.soft_delete(widget)

    async def get_widget_metrics(
        self, organization_id: UUID, widget_id: UUID
    ) -> WidgetMetricsResponse:
        widget = await self.widget_repo.get_by_id_for_org(widget_id, organization_id)
        if not widget:
            raise NotFoundError("Widget not found")

        query = widget.query or {}
        time_range = query.get("time_range", "24h")
        start, end = self.event_repo.parse_time_range(time_range)
        event_name = query.get("event_name")
        metric = query.get("metric", "count")
        group_by = query.get("group_by")
        granularity = query.get("granularity", "1h")

        if widget.type == "kpi" or metric == "count":
            if group_by and widget.type != "kpi":
                rows = await self.event_repo.aggregate_count(
                    organization_id, event_name, start, end, group_by, granularity
                )
                data = [MetricDataPoint(label=r["label"], value=r["value"], timestamp=r.get("timestamp")) for r in rows]
                total = sum(d.value for d in data)
            else:
                total = await self.event_repo.aggregate_total(
                    organization_id, event_name, start, end
                )
                data = [MetricDataPoint(label="total", value=total)]
            return WidgetMetricsResponse(
                widget_id=widget.id,
                type=widget.type,
                data=data,
                total=total if isinstance(total, float) else data[0].value if data else 0,
            )

        rows = await self.event_repo.aggregate_count(
            organization_id, event_name, start, end, group_by, granularity
        )
        data = [
            MetricDataPoint(label=r.get("label", "count"), value=r["value"], timestamp=r.get("timestamp"))
            for r in rows
        ]
        return WidgetMetricsResponse(widget_id=widget.id, type=widget.type, data=data)
