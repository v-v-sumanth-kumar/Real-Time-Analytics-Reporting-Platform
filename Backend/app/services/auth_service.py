from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.core.permissions import ROLE_LABELS, Role
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import AuthResponse, OrganizationResponse, UserResponse


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.org_repo = OrganizationRepository(session)
        self.refresh_repo = RefreshTokenRepository(session)

    def _user_response(self, user) -> UserResponse:
        return UserResponse.model_validate(user)

    def _org_response(self, org) -> OrganizationResponse:
        return OrganizationResponse.model_validate(org)

    async def signup(
        self,
        email: str,
        password: str,
        full_name: str,
        organization_name: str,
    ) -> tuple[AuthResponse, str]:
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ConflictError("Email already registered")

        user = await self.user_repo.create(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
        )
        org = await self.org_repo.create(name=organization_name)
        await self.org_repo.add_member(org.id, user.id, Role.OWNER)

        access = create_access_token(user.id, org_id=org.id)
        refresh_token_str = create_refresh_token(user.id)
        await self._store_refresh(user.id, refresh_token_str)

        return (
            AuthResponse(
                access_token=access,
                user=self._user_response(user),
                organization=self._org_response(org),
                role=self.member_role_label(int(Role.OWNER)),
            ),
            refresh_token_str,
        )

    async def login(self, email: str, password: str) -> tuple[AuthResponse, str]:
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedError("Account is disabled")

        orgs = await self.org_repo.list_user_organizations(user.id)
        org = orgs[0] if orgs else None
        role: str | None = None
        if org:
            member = await self.org_repo.get_member(org.id, user.id)
            if member:
                role = self.member_role_label(member.role)
        access = create_access_token(user.id, org_id=org.id if org else None)
        refresh_str = create_refresh_token(user.id)
        await self._store_refresh(user.id, refresh_str)

        return (
            AuthResponse(
                access_token=access,
                user=self._user_response(user),
                organization=self._org_response(org) if org else None,
                role=role,
            ),
            refresh_str,
        )

    async def refresh_access_token(
        self, refresh_token: str
    ) -> tuple[AuthResponse, str | None]:
        try:
            payload = decode_token(refresh_token)
        except ValueError as e:
            raise UnauthorizedError("Invalid refresh token") from e

        if payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid token type")

        token_hash = hash_token(refresh_token)
        stored = await self.refresh_repo.get_by_hash(token_hash)
        if not stored or stored.expires_at < datetime.now(timezone.utc):
            raise UnauthorizedError("Refresh token expired or revoked")

        user = await self.user_repo.get_by_id(UUID(payload["sub"]))
        if not user or not user.is_active:
            raise UnauthorizedError("User not found")

        await self.refresh_repo.revoke(stored)

        orgs = await self.org_repo.list_user_organizations(user.id)
        org = orgs[0] if orgs else None
        role: str | None = None
        if org:
            member = await self.org_repo.get_member(org.id, user.id)
            if member:
                role = self.member_role_label(member.role)
        access = create_access_token(user.id, org_id=org.id if org else None)
        new_refresh = create_refresh_token(user.id)
        await self._store_refresh(user.id, new_refresh)

        return (
            AuthResponse(
                access_token=access,
                user=self._user_response(user),
                organization=self._org_response(org) if org else None,
                role=role,
            ),
            new_refresh,
        )

    async def get_me(self, user_id: UUID, org_id: UUID | None) -> "MeResponse":
        from app.schemas.common import MeResponse, OrganizationResponse, UserResponse

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        org = None
        role = None
        if org_id:
            org_model = await self.org_repo.get_by_id(org_id)
            if org_model:
                org = OrganizationResponse.model_validate(org_model)
                member = await self.org_repo.get_member(org_id, user_id)
                if member:
                    role = self.member_role_label(member.role)
        else:
            orgs = await self.org_repo.list_user_organizations(user_id)
            if orgs:
                org = OrganizationResponse.model_validate(orgs[0])
                member = await self.org_repo.get_member(orgs[0].id, user_id)
                if member:
                    role = self.member_role_label(member.role)
        return MeResponse(
            user=UserResponse.model_validate(user),
            organization=org,
            role=role,
        )

    async def logout(self, refresh_token: str | None) -> None:
        if refresh_token:
            token_hash = hash_token(refresh_token)
            stored = await self.refresh_repo.get_by_hash(token_hash)
            if stored:
                await self.refresh_repo.revoke(stored)

    async def _store_refresh(self, user_id: UUID, token: str) -> str:
        from app.core.config import get_settings
        settings = get_settings()
        expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        await self.refresh_repo.create(
            user_id=user_id,
            token_hash=hash_token(token),
            expires_at=expires,
        )
        return token

    @staticmethod
    def member_role_label(role_int: int) -> str:
        return ROLE_LABELS.get(Role(role_int), "viewer")
