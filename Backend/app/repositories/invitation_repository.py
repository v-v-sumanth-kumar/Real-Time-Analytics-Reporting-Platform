from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invitation import Invitation
from app.repositories.base import BaseRepository


class InvitationRepository(BaseRepository[Invitation]):
    model = Invitation

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(
        self,
        organization_id: UUID,
        email: str,
        role: int,
        token_hash: str,
        invited_by: UUID,
        expires_at: datetime,
    ) -> Invitation:
        inv = Invitation(
            organization_id=organization_id,
            email=email.lower(),
            role=role,
            token_hash=token_hash,
            invited_by=invited_by,
            expires_at=expires_at,
        )
        self.session.add(inv)
        await self.session.flush()
        return inv

    async def get_by_token_hash(self, token_hash: str) -> Invitation | None:
        stmt = select(Invitation).where(
            Invitation.token_hash == token_hash,
            Invitation.accepted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_pending_by_email(
        self, organization_id: UUID, email: str
    ) -> Invitation | None:
        stmt = select(Invitation).where(
            Invitation.organization_id == organization_id,
            Invitation.email == email.lower(),
            Invitation.accepted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
