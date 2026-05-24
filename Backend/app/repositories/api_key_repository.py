from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey
from app.repositories.base import BaseRepository


class ApiKeyRepository(BaseRepository[ApiKey]):
    model = ApiKey

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(self, **kwargs) -> ApiKey:
        key = ApiKey(**kwargs)
        self.session.add(key)
        await self.session.flush()
        return key

    async def list_by_org(self, organization_id: UUID) -> list[ApiKey]:
        stmt = self._active(
            select(ApiKey)
            .where(ApiKey.organization_id == organization_id)
            .order_by(ApiKey.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_prefix_and_hash(self, prefix: str, key_hash: str) -> ApiKey | None:
        stmt = self._active(
            select(ApiKey).where(
                ApiKey.key_prefix == prefix,
                ApiKey.key_hash == key_hash,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
