from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
import hashlib

from app.core.security import generate_api_key
from app.repositories.api_key_repository import ApiKeyRepository
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyResponse


class ApiKeyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ApiKeyRepository(session)

    async def create(
        self, organization_id: UUID, data: ApiKeyCreate
    ) -> ApiKeyCreatedResponse:
        full_key, prefix, key_hash = generate_api_key()
        api_key = await self.repo.create(
            organization_id=organization_id,
            name=data.name,
            key_prefix=prefix,
            key_hash=key_hash,
            rate_limit_rpm=data.rate_limit_rpm,
        )
        resp = ApiKeyResponse.model_validate(api_key)
        return ApiKeyCreatedResponse(**resp.model_dump(), key=full_key)

    async def list(self, organization_id: UUID) -> list[ApiKeyResponse]:
        keys = await self.repo.list_by_org(organization_id)
        return [ApiKeyResponse.model_validate(k) for k in keys]

    async def revoke(self, organization_id: UUID, key_id: UUID) -> None:
        key = await self.repo.get_by_id(key_id)
        if not key or key.organization_id != organization_id:
            raise NotFoundError("API key not found")
        await self.repo.soft_delete(key)

    async def rotate(
        self, organization_id: UUID, key_id: UUID, data: ApiKeyCreate | None = None
    ) -> ApiKeyCreatedResponse:
        old = await self.repo.get_by_id(key_id)
        if not old or old.organization_id != organization_id:
            raise NotFoundError("API key not found")
        name = data.name if data else old.name
        rate_limit = data.rate_limit_rpm if data else old.rate_limit_rpm
        await self.repo.soft_delete(old)
        full_key, prefix, key_hash = generate_api_key()
        api_key = await self.repo.create(
            organization_id=organization_id,
            name=name,
            key_prefix=prefix,
            key_hash=key_hash,
            rate_limit_rpm=rate_limit,
        )
        resp = ApiKeyResponse.model_validate(api_key)
        return ApiKeyCreatedResponse(**resp.model_dump(), key=full_key)

    async def validate_key(self, api_key_header: str):
        if not api_key_header.startswith("ak_"):
            raise NotFoundError("Invalid API key")
        key_hash = hashlib.sha256(api_key_header.encode()).hexdigest()
        raw = api_key_header[3:]
        prefix = raw[:8]
        key = await self.repo.get_by_prefix_and_hash(prefix, key_hash)
        if not key:
            raise NotFoundError("Invalid API key")
        if key.expires_at and key.expires_at < datetime.now(timezone.utc):
            raise NotFoundError("API key expired")
        key.last_used_at = datetime.now(timezone.utc)
        await self.session.flush()
        return key
