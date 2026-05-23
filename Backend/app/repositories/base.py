from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base, SoftDeleteMixin

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _active(self, stmt: Select) -> Select:
        if issubclass(self.model, SoftDeleteMixin):
            return stmt.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        return stmt

    async def get_by_id(self, entity_id: UUID) -> ModelT | None:
        stmt = self._active(select(self.model).where(self.model.id == entity_id))  # type: ignore[attr-defined]
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def soft_delete(self, entity: ModelT) -> None:
        if isinstance(entity, SoftDeleteMixin):
            from app.db.base import utc_now
            entity.deleted_at = utc_now()  # type: ignore[attr-defined]
            await self.session.flush()
