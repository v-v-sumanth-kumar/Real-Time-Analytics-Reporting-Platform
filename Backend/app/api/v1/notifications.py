from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.core.deps import get_current_member, get_db_notification_service, require_role
from app.core.permissions import Role
from app.models.organization import OrganizationMember
from app.repositories.alert_repository import NotificationRepository
from app.schemas.alert import NotificationResponse
from app.services.notification_service import NotificationService
from app.utils.pagination import PaginationParams
from app.utils.response import PaginationMeta, success_response

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    request: Request,
    params: PaginationParams = Depends(),
    member: OrganizationMember = Depends(require_role(Role.VIEWER)),
    service: NotificationService = Depends(get_db_notification_service),
):
    result = await service.list(member.organization_id, member.user_id, params)
    meta = PaginationMeta(
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        total_pages=result.total_pages,
    )
    return success_response(
        [n.model_dump() for n in result.items],
        meta=meta,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: UUID,
    request: Request,
    member: OrganizationMember = Depends(require_role(Role.VIEWER)),
    service: NotificationService = Depends(get_db_notification_service),
):
    notif = await service.mark_read(notification_id, member.organization_id)
    if not notif:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Notification not found")
    return success_response(
        NotificationResponse.model_validate(notif).model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )
