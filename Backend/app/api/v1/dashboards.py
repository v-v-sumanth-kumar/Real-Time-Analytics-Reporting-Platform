from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.core.deps import get_current_member, get_dashboard_service, require_role
from app.core.permissions import Role
from app.models.organization import OrganizationMember
from app.schemas.dashboard import (
    DashboardCreate,
    DashboardUpdate,
    WidgetCreate,
    WidgetUpdate,
)
from app.services.dashboard_service import DashboardService
from app.utils.pagination import PaginationParams
from app.utils.response import PaginationMeta, success_response

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.get("")
async def list_dashboards(
    request: Request,
    params: PaginationParams = Depends(),
    member: OrganizationMember = Depends(require_role(Role.VIEWER)),
    service: DashboardService = Depends(get_dashboard_service),
):
    result = await service.list(member.organization_id, params)
    meta = PaginationMeta(
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )
    return success_response(
        [d.model_dump() for d in result.items],
        meta=meta,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_dashboard(
    body: DashboardCreate,
    request: Request,
    member: OrganizationMember = Depends(require_role(Role.ANALYST)),
    service: DashboardService = Depends(get_dashboard_service),
):
    dashboard = await service.create(member.organization_id, member.user_id, body)
    return success_response(
        dashboard.model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/public/{share_token}")
async def get_public_dashboard(
    share_token: str,
    request: Request,
    service: DashboardService = Depends(get_dashboard_service),
):
    dashboard = await service.get_public(share_token)
    return success_response(
        dashboard.model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/{dashboard_id}")
async def get_dashboard(
    dashboard_id: UUID,
    request: Request,
    member: OrganizationMember = Depends(require_role(Role.VIEWER)),
    service: DashboardService = Depends(get_dashboard_service),
):
    dashboard = await service.get(member.organization_id, dashboard_id)
    return success_response(
        dashboard.model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.patch("/{dashboard_id}")
async def update_dashboard(
    dashboard_id: UUID,
    body: DashboardUpdate,
    request: Request,
    member: OrganizationMember = Depends(require_role(Role.ANALYST)),
    service: DashboardService = Depends(get_dashboard_service),
):
    dashboard = await service.update(member.organization_id, dashboard_id, body)
    return success_response(
        dashboard.model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.delete("/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard(
    dashboard_id: UUID,
    member: OrganizationMember = Depends(require_role(Role.ADMIN)),
    service: DashboardService = Depends(get_dashboard_service),
):
    await service.delete(member.organization_id, dashboard_id)


@router.post("/{dashboard_id}/widgets", status_code=status.HTTP_201_CREATED)
async def add_widget(
    dashboard_id: UUID,
    body: WidgetCreate,
    request: Request,
    member: OrganizationMember = Depends(require_role(Role.ANALYST)),
    service: DashboardService = Depends(get_dashboard_service),
):
    widget = await service.add_widget(member.organization_id, dashboard_id, body)
    return success_response(
        widget.model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.patch("/widgets/{widget_id}")
async def update_widget(
    widget_id: UUID,
    body: WidgetUpdate,
    request: Request,
    member: OrganizationMember = Depends(require_role(Role.ANALYST)),
    service: DashboardService = Depends(get_dashboard_service),
):
    widget = await service.update_widget(member.organization_id, widget_id, body)
    return success_response(
        widget.model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.delete("/widgets/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_widget(
    widget_id: UUID,
    member: OrganizationMember = Depends(require_role(Role.ANALYST)),
    service: DashboardService = Depends(get_dashboard_service),
):
    await service.delete_widget(member.organization_id, widget_id)


@router.get("/widgets/{widget_id}/metrics")
async def widget_metrics(
    widget_id: UUID,
    request: Request,
    member: OrganizationMember = Depends(require_role(Role.VIEWER)),
    service: DashboardService = Depends(get_dashboard_service),
):
    metrics = await service.get_widget_metrics(member.organization_id, widget_id)
    return success_response(
        metrics.model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )
