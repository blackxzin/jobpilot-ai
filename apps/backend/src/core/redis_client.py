"""JobPilot AI — Redis Client (singleton pattern)."""
from __future__ import annotations

import redis.asyncio as aioredis

from core.config import settings

_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Get or create a Redis client singleton."""
    global _redis_client
    if _redis_client is None or _redis_client.connection_pool is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20,
        )
    return _redis_client


async def close_redis() -> None:
    """Close the Redis connection."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
