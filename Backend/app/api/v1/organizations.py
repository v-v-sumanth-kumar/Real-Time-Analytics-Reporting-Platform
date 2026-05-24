from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import (
    get_current_organization,
    get_current_user,
    get_invitation_service,
    require_role,
)
from app.core.permissions import Role
from app.db.session import get_db_session
from app.models.organization import Organization, OrganizationMember
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.auth import InviteAcceptRequest, InviteCreateRequest
from app.schemas.common import MemberResponse, OrganizationResponse
from app.services.auth_service import AuthService
from app.services.invitation_service import InvitationService
from app.utils.frontend_url import resolve_frontend_base_url
from app.utils.response import success_response

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/current")
async def get_current_org(
    request: Request,
    org: Organization = Depends(get_current_organization),
):
    return success_response(
        OrganizationResponse.model_validate(org).model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/members")
async def list_members(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    org: Organization = Depends(get_current_organization),
    member: OrganizationMember = Depends(require_role(Role.VIEWER)),
):
    repo = OrganizationRepository(session)
    members = await repo.list_members(org.id)

    data = []
    for m in members:
        data.append(
            MemberResponse(
                id=m.id,
                user_id=m.user_id,
                organization_id=m.organization_id,
                role=AuthService.member_role_label(m.role),
                email=m.user.email if m.user else None,
                full_name=m.user.full_name if m.user else None,
            ).model_dump()
        )
    return success_response(data, correlation_id=getattr(request.state, "correlation_id", None))


@router.post("/invitations")
async def invite_user(
    body: InviteCreateRequest,
    request: Request,
    user: User = Depends(get_current_user),
    member: OrganizationMember = Depends(require_role(Role.ADMIN)),
    service: InvitationService = Depends(get_invitation_service),
):
    token, info = await service.create_invitation(
        member.organization_id,
        body.email,
        body.role_enum(),
        user.id,
    )
    base = resolve_frontend_base_url(request)
    info["invite_link"] = f"{base}/accept-invite?token={token}"
    return success_response(info, correlation_id=getattr(request.state, "correlation_id", None))


@router.post("/invitations/accept")
async def accept_invite(
    body: InviteAcceptRequest,
    request: Request,
    service: InvitationService = Depends(get_invitation_service),
):
    user_id = await service.accept_invitation(body.token, body.password, body.full_name)
    return success_response(
        {"user_id": str(user_id), "message": "Invitation accepted"},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
