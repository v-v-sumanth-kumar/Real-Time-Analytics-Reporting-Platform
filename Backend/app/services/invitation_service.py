from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.core.permissions import Role
from app.core.security import generate_invite_token, hash_password, hash_token
from app.repositories.invitation_repository import InvitationRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository


class InvitationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.invite_repo = InvitationRepository(session)
        self.org_repo = OrganizationRepository(session)
        self.user_repo = UserRepository(session)

    async def create_invitation(
        self,
        organization_id: UUID,
        email: str,
        role: Role,
        invited_by: UUID,
    ) -> tuple[str, dict]:
        pending = await self.invite_repo.get_pending_by_email(organization_id, email)
        if pending:
            raise ConflictError("Invitation already pending for this email")

        member = await self.user_repo.get_by_email(email)
        if member:
            existing = await self.org_repo.get_member(organization_id, member.id)
            if existing:
                raise ConflictError("User is already a member")

        raw_token, token_hash = generate_invite_token()
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        inv = await self.invite_repo.create(
            organization_id=organization_id,
            email=email,
            role=int(role),
            token_hash=token_hash,
            invited_by=invited_by,
            expires_at=expires,
        )
        from app.core.permissions import ROLE_LABELS
        return raw_token, {
            "id": str(inv.id),
            "email": inv.email,
            "role": ROLE_LABELS.get(role, "viewer"),
            "expires_at": inv.expires_at.isoformat(),
        }

    async def accept_invitation(
        self,
        token: str,
        password: str | None,
        full_name: str | None,
    ) -> UUID:
        token_hash = hash_token(token)
        inv = await self.invite_repo.get_by_token_hash(token_hash)
        if not inv:
            raise NotFoundError("Invalid invitation token")
        if inv.expires_at < datetime.now(timezone.utc):
            raise UnauthorizedError("Invitation expired")

        user = await self.user_repo.get_by_email(inv.email)
        if not user:
            if not password or not full_name:
                raise UnauthorizedError("Password and full name required for new users")
            user = await self.user_repo.create(
                email=inv.email,
                password_hash=hash_password(password),
                full_name=full_name,
            )

        await self.org_repo.add_member(
            inv.organization_id, user.id, Role(inv.role)
        )
        inv.accepted_at = datetime.now(timezone.utc)
        await self.session.flush()
        return user.id
