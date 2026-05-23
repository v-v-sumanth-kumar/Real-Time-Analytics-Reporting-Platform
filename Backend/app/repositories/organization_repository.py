import re
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.permissions import Role
from app.models.organization import Organization, OrganizationMember
from app.models.user import User
from app.repositories.base import BaseRepository


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:80] or "org"


class OrganizationRepository(BaseRepository[Organization]):
    model = Organization

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(self, name: str, slug: str | None = None) -> Organization:
        base_slug = slug or slugify(name)
        unique_slug = base_slug
        counter = 1
        while await self.get_by_slug(unique_slug):
            unique_slug = f"{base_slug}-{counter}"
            counter += 1

        org = Organization(name=name, slug=unique_slug)
        self.session.add(org)
        await self.session.flush()
        return org

    async def get_by_slug(self, slug: str) -> Organization | None:
        stmt = self._active(select(Organization).where(Organization.slug == slug))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_member(
        self, organization_id: UUID, user_id: UUID, role: Role
    ) -> OrganizationMember:
        member = OrganizationMember(
            organization_id=organization_id,
            user_id=user_id,
            role=int(role),
        )
        self.session.add(member)
        await self.session.flush()
        return member

    async def get_member(
        self, organization_id: UUID, user_id: UUID
    ) -> OrganizationMember | None:
        stmt = self._active(
            select(OrganizationMember)
            .where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
            )
            .options(selectinload(OrganizationMember.user))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_members(self, organization_id: UUID) -> list[OrganizationMember]:
        stmt = (
            self._active(
                select(OrganizationMember)
                .where(OrganizationMember.organization_id == organization_id)
                .options(selectinload(OrganizationMember.user))
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_user_organizations(self, user_id: UUID) -> list[Organization]:
        stmt = (
            self._active(
                select(Organization)
                .join(OrganizationMember)
                .where(OrganizationMember.user_id == user_id)
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_members(self, organization_id: UUID) -> int:
        stmt = select(func.count()).select_from(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
