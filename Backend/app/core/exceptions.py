from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.utils.response import error_response


class AppException(Exception):
    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message=message, code="NOT_FOUND", status_code=404)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message=message, code="UNAUTHORIZED", status_code=401)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message=message, code="FORBIDDEN", status_code=403)


class ConflictError(AppException):
    def __init__(self, message: str = "Conflict") -> None:
        super().__init__(message=message, code="CONFLICT", status_code=409)


class RateLimitError(AppException):
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60) -> None:
        super().__init__(message=message, code="RATE_LIMIT", status_code=429)
        self.retry_after = retry_after


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", None)
    body = error_response(
        message=exc.message,
        code=exc.code,
        details=exc.details,
        correlation_id=correlation_id,
    )
    headers = {}
    if isinstance(exc, RateLimitError):
        headers["Retry-After"] = str(exc.retry_after)
    return JSONResponse(status_code=exc.status_code, content=body, headers=headers)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", None)
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    body = error_response(
        message=detail,
        code="HTTP_ERROR",
        correlation_id=correlation_id,
    )
    return JSONResponse(status_code=exc.status_code, content=body)
