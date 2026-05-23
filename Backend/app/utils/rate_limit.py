import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.exceptions import RateLimitError


class RateLimiter:
    def __init__(self, redis_client: aioredis.Redis) -> None:
        self.redis = redis_client
        self.settings = get_settings()

    async def check_org_ingest_limit(self, organization_id: str) -> None:
        """Sliding window rate limit per organization per minute."""
        key = f"ratelimit:ingest:org:{organization_id}"
        limit = self.settings.ingest_rate_limit_per_minute

        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, 60)
        results = await pipe.execute()
        current = int(results[0])

        if current > limit:
            raise RateLimitError(
                message=f"Ingest rate limit exceeded ({limit}/min)",
                retry_after=60,
            )
