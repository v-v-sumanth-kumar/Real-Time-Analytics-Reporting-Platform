from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    rate_limit_rpm: int = Field(default=10000, ge=1, le=100000)


class ApiKeyResponse(ORMBase):
    id: UUID
    name: str
    key_prefix: str
    rate_limit_rpm: int
    last_used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime


class ApiKeyCreatedResponse(ApiKeyResponse):
    key: str  # only returned once at creation
