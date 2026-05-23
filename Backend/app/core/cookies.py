"""Refresh-token cookie settings for local and cross-origin (SPA) deployments."""

from typing import Literal

from app.core.config import get_settings

SameSite = Literal["lax", "none", "strict"]
REFRESH_COOKIE = "refresh_token"


def refresh_cookie_params() -> dict:
    """
    Cross-origin frontends (e.g. Vercel) calling an API on another host (e.g. Render)
    need SameSite=None and Secure=True or the browser will not send refresh_token.
    """
    settings = get_settings()
    samesite: SameSite
    if settings.cookie_samesite in ("lax", "none", "strict"):
        samesite = settings.cookie_samesite  # type: ignore[assignment]
    elif settings.cookie_secure:
        samesite = "none"
    else:
        samesite = "lax"

    secure = settings.cookie_secure or samesite == "none"
    if samesite == "none" and not secure:
        secure = True

    return {
        "key": REFRESH_COOKIE,
        "httponly": True,
        "secure": secure,
        "samesite": samesite,
        "max_age": settings.refresh_token_expire_days * 86400,
        "domain": settings.cookie_domain or None,
        "path": "/",
    }
