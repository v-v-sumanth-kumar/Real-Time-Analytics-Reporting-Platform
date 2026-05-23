from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    meta: PaginationMeta | dict[str, Any] | None = None
    correlation_id: str | None = None


def success_response(
    data: Any,
    *,
    meta: PaginationMeta | dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    return APIResponse(success=True, data=data, meta=meta, correlation_id=correlation_id).model_dump(
        mode="json"
    )


def error_response(
    message: str,
    *,
    code: str = "ERROR",
    details: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    return {
        "success": False,
        "error": {"message": message, "code": code, "details": details or {}},
        "correlation_id": correlation_id,
    }
