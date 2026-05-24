from urllib.parse import urlparse

from fastapi import Request

from app.core.config import get_settings


def _is_local_url(url: str) -> bool:
    if not url:
        return True
    host = (urlparse(url).hostname or "").lower()
    return host in ("localhost", "127.0.0.1", "0.0.0.0")


def resolve_frontend_base_url(request: Request | None = None) -> str:
    """Public URL for invite/share links.

    Priority:
    1. FRONTEND_URL env when set to a non-localhost URL (production config)
    2. Browser Origin header (when admin uses a deployed UI but backend env is still localhost)
    3. FRONTEND_URL / Origin fallback (local dev)
    """
    settings = get_settings()
    configured = settings.frontend_url.rstrip("/")
    origin = ""
    if request is not None:
        origin = (request.headers.get("origin") or "").rstrip("/")

    if configured and not _is_local_url(configured):
        return configured
    if origin and not _is_local_url(origin):
        return origin
    return configured or origin or "http://localhost:3000"
