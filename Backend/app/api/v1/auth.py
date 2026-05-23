from fastapi import APIRouter, Cookie, Depends, Request, Response, status

from app.core.config import get_settings
from app.core.deps import (
    get_auth_service,
    get_current_user,
    get_refresh_token,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, SignupRequest
from app.schemas.common import AuthResponse, MessageResponse, UserResponse
from app.services.auth_service import AuthService
from app.utils.response import success_response

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"


def _set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
        domain=settings.cookie_domain or None,
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=REFRESH_COOKIE,
        path="/",
        domain=settings.cookie_domain or None,
    )


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(
    body: SignupRequest,
    response: Response,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    auth, refresh = await service.signup(
        body.email, body.password, body.full_name, body.organization_name
    )
    _set_refresh_cookie(response, refresh)
    return success_response(
        auth.model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("/login")
async def login(
    body: LoginRequest,
    response: Response,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    auth, refresh = await service.login(body.email, body.password)
    _set_refresh_cookie(response, refresh)
    return success_response(
        auth.model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("/refresh")
async def refresh(
    response: Response,
    request: Request,
    refresh_token: str = Depends(get_refresh_token),
    service: AuthService = Depends(get_auth_service),
):
    auth, new_refresh = await service.refresh_access_token(refresh_token)
    if new_refresh:
        _set_refresh_cookie(response, new_refresh)
    return success_response(
        auth.model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    service: AuthService = Depends(get_auth_service),
    refresh_token: str | None = Cookie(default=None, alias="refresh_token"),
):
    if refresh_token:
        await service.logout(refresh_token)
    _clear_refresh_cookie(response)
    return success_response(
        MessageResponse(message="Logged out").model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/me")
async def me(
    request: Request,
    user: User = Depends(get_current_user),
):
    return success_response(
        UserResponse.model_validate(user).model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )
