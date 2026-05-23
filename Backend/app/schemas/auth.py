from pydantic import BaseModel, EmailStr, Field

from app.core.permissions import Role


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    organization_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    pass  # refresh via cookie


class InviteAcceptRequest(BaseModel):
    token: str
    password: str | None = Field(default=None, min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class InviteCreateRequest(BaseModel):
    email: EmailStr
    role: str = "viewer"

    def role_enum(self) -> Role:
        from app.core.permissions import role_from_label
        return role_from_label(self.role)
