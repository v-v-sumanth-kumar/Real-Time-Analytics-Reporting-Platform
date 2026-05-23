from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.core.deps import get_alert_service, get_current_member, require_role
from app.core.permissions import Role
from app.models.organization import OrganizationMember
from app.schemas.alert import AlertMuteRequest, AlertRuleCreate, AlertRuleUpdate
from app.services.alert_service import AlertService
from app.utils.pagination import PaginationParams
from app.utils.response import PaginationMeta, success_response

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
async def list_alerts(
    request: Request,
    params: PaginationParams = Depends(),
    member: OrganizationMember = Depends(require_role(Role.VIEWER)),
    service: AlertService = Depends(get_alert_service),
):
    result = await service.list(member.organization_id, params)
    meta = PaginationMeta(
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )
    return success_response(
        [a.model_dump() for a in result.items],
        meta=meta,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_alert(
    body: AlertRuleCreate,
    request: Request,
    member: OrganizationMember = Depends(require_role(Role.ANALYST)),
    service: AlertService = Depends(get_alert_service),
):
    alert = await service.create(member.organization_id, member.user_id, body)
    return success_response(
        alert.model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/{alert_id}")
async def get_alert(
    alert_id: UUID,
    request: Request,
    member: OrganizationMember = Depends(require_role(Role.VIEWER)),
    service: AlertService = Depends(get_alert_service),
):
    alert = await service.get(member.organization_id, alert_id)
    return success_response(
        alert.model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.patch("/{alert_id}")
async def update_alert(
    alert_id: UUID,
    body: AlertRuleUpdate,
    request: Request,
    member: OrganizationMember = Depends(require_role(Role.ANALYST)),
    service: AlertService = Depends(get_alert_service),
):
    alert = await service.update(member.organization_id, alert_id, body)
    return success_response(
        alert.model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: UUID,
    member: OrganizationMember = Depends(require_role(Role.ADMIN)),
    service: AlertService = Depends(get_alert_service),
):
    await service.delete(member.organization_id, alert_id)


@router.post("/{alert_id}/mute")
async def mute_alert(
    alert_id: UUID,
    body: AlertMuteRequest,
    request: Request,
    member: OrganizationMember = Depends(require_role(Role.ANALYST)),
    service: AlertService = Depends(get_alert_service),
):
    alert = await service.mute(member.organization_id, alert_id, body.minutes)
    return success_response(
        alert.model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("/{alert_id}/unmute")
async def unmute_alert(
    alert_id: UUID,
    request: Request,
    member: OrganizationMember = Depends(require_role(Role.ANALYST)),
    service: AlertService = Depends(get_alert_service),
):
    alert = await service.unmute(member.organization_id, alert_id)
    return success_response(
        alert.model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/{alert_id}/history")
async def alert_history(
    alert_id: UUID,
    request: Request,
    params: PaginationParams = Depends(),
    member: OrganizationMember = Depends(require_role(Role.VIEWER)),
    service: AlertService = Depends(get_alert_service),
):
    result = await service.list_incidents(member.organization_id, alert_id, params)
    meta = PaginationMeta(
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )
    return success_response(
        [i.model_dump() for i in result.items],
        meta=meta,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
