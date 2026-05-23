from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class IDResponse(BaseModel):
    id: UUID


class MessageResponse(BaseModel):
    message: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"
    organization: "OrganizationResponse | None" = None


class UserResponse(ORMBase):
    id: UUID
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime


class OrganizationResponse(ORMBase):
    id: UUID
    name: str
    slug: str
    plan: str
    created_at: datetime


class MemberResponse(ORMBase):
    id: UUID
    user_id: UUID
    organization_id: UUID
    role: str
    email: EmailStr | None = None
    full_name: str | None = None


AuthResponse.model_rebuild()
