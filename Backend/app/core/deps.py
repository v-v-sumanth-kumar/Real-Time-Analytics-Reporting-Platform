from typing import Annotated
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import Cookie, Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.permissions import Role, has_permission
from app.core.security import decode_token
from app.db.session import get_db_session
from app.models.api_key import ApiKey
from app.models.organization import Organization, OrganizationMember
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository
from app.services.api_key_service import ApiKeyService
from app.services.auth_service import AuthService
from app.services.dashboard_service import DashboardService
from app.services.ingestion_service import IngestionService
from app.services.invitation_service import InvitationService

security = HTTPBearer(auto_error=False)

_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthService:
    return AuthService(session)


async def get_invitation_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> InvitationService:
    return InvitationService(session)


async def get_ingestion_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
) -> IngestionService:
    return IngestionService(session, redis)


async def get_dashboard_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DashboardService:
    return DashboardService(session)


async def get_api_key_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiKeyService:
    return ApiKeyService(session)


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> User:
    if not credentials:
        raise UnauthorizedError("Missing authentication")
    try:
        payload = decode_token(credentials.credentials)
    except ValueError as e:
        raise UnauthorizedError("Invalid token") from e
    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")
    user = await UserRepository(session).get_by_id(UUID(payload["sub"]))
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    return user


async def get_current_org_id(
    x_organization_id: Annotated[str | None, Header(alias="X-Organization-ID")] = None,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
) -> UUID | None:
    if x_organization_id:
        return UUID(x_organization_id)
    if credentials:
        try:
            payload = decode_token(credentials.credentials)
            if payload.get("org_id"):
                return UUID(payload["org_id"])
        except (ValueError, KeyError):
            pass
    return None


async def get_current_member(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
    org_id: Annotated[UUID | None, Depends(get_current_org_id)],
) -> OrganizationMember:
    if not org_id:
        orgs = await OrganizationRepository(session).list_user_organizations(user.id)
        if not orgs:
            raise ForbiddenError("No organization context")
        org_id = orgs[0].id

    member = await OrganizationRepository(session).get_member(org_id, user.id)
    if not member:
        raise ForbiddenError("Not a member of this organization")
    return member


async def get_current_organization(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    member: Annotated[OrganizationMember, Depends(get_current_member)],
) -> Organization:
    org = await OrganizationRepository(session).get_by_id(member.organization_id)
    if not org:
        raise NotFoundError("Organization not found")
    return org


def require_role(min_role: Role):
    async def _guard(
        member: Annotated[OrganizationMember, Depends(get_current_member)],
    ) -> OrganizationMember:
        if not has_permission(Role(member.role), min_role):
            raise ForbiddenError(f"Requires {min_role.name.lower()} role or higher")
        return member

    return _guard


async def get_org_from_api_key(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> ApiKey:
    if not x_api_key:
        raise UnauthorizedError("API key required")
    service = ApiKeyService(session)
    try:
        return await service.validate_key(x_api_key)
    except NotFoundError as e:
        raise UnauthorizedError("Invalid API key") from e


async def get_refresh_token(
    refresh_token: Annotated[str | None, Cookie(alias="refresh_token")] = None,
) -> str:
    if not refresh_token:
        raise UnauthorizedError("Refresh token missing")
    return refresh_token
