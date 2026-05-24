from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import get_settings
from app.core.deps import get_redis
from app.db.session import engine

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    settings = get_settings()
    checks = {"api": "ok", "database": "unknown", "redis": "unknown"}
    http_status = status.HTTP_200_OK

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    try:
        redis = await get_redis()
        await redis.ping()
        checks["redis"] = "ok"
        checks["ingest_queue_depth"] = await redis.llen("ingest:events")
        checks["csv_queue_depth"] = await redis.llen("ingest:csv")
    except Exception as e:
        checks["redis"] = f"error: {e}"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=http_status,
        content={"status": "healthy" if http_status == 200 else "degraded", "checks": checks, "env": settings.app_env},
    )
