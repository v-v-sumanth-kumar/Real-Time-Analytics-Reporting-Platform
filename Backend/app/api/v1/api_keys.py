from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.core.deps import get_api_key_service, require_role
from app.core.permissions import Role
from app.models.organization import OrganizationMember
from app.schemas.api_key import ApiKeyCreate
from app.services.api_key_service import ApiKeyService
from app.utils.response import success_response

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("")
async def list_keys(
    request: Request,
    member: OrganizationMember = Depends(require_role(Role.ADMIN)),
    service: ApiKeyService = Depends(get_api_key_service),
):
    keys = await service.list(member.organization_id)
    return success_response(
        [k.model_dump() for k in keys],
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_key(
    body: ApiKeyCreate,
    request: Request,
    member: OrganizationMember = Depends(require_role(Role.ADMIN)),
    service: ApiKeyService = Depends(get_api_key_service),
):
    key = await service.create(member.organization_id, body)
    return success_response(
        key.model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_key(
    key_id: UUID,
    member: OrganizationMember = Depends(require_role(Role.ADMIN)),
    service: ApiKeyService = Depends(get_api_key_service),
):
    await service.revoke(member.organization_id, key_id)


@router.post("/{key_id}/rotate", status_code=status.HTTP_201_CREATED)
async def rotate_key(
    key_id: UUID,
    request: Request,
    member: OrganizationMember = Depends(require_role(Role.ADMIN)),
    service: ApiKeyService = Depends(get_api_key_service),
):
    key = await service.rotate(member.organization_id, key_id)
    return success_response(
        key.model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )
