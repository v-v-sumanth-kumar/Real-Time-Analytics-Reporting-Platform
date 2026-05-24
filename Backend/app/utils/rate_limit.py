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

    async def check_api_key_limit(self, api_key_id: str, limit_rpm: int) -> None:
        """Sliding window rate limit per API key per minute."""
        key = f"ratelimit:ingest:apikey:{api_key_id}"
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, 60)
        results = await pipe.execute()
        current = int(results[0])
        if current > limit_rpm:
            raise RateLimitError(
                message=f"API key rate limit exceeded ({limit_rpm}/min)",
                retry_after=60,
            )
