"""JobPilot AI — Redis client.

The client is a singleton, but it is bound to the event loop that created it:
its connection pool holds loop-specific primitives. Reusing it from a
different loop raises "Event loop is closed" or hangs, so the loop it belongs
to is tracked and the client is rebuilt whenever it changes.

That happens for real in tests, where each case runs on a fresh loop, and in
any process that restarts its loop — a Celery worker between tasks, for
instance. Without the check the failure is silent: callers fall back to
degraded behaviour instead of using Redis at all.
"""
from __future__ import annotations

import asyncio

import redis.asyncio as aioredis

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

_redis_client: aioredis.Redis | None = None
_client_loop: asyncio.AbstractEventLoop | None = None


async def get_redis() -> aioredis.Redis:
    """Return a Redis client valid for the running event loop."""
    global _redis_client, _client_loop

    loop = asyncio.get_running_loop()

    if _redis_client is not None and (_client_loop is not loop or loop.is_closed()):
        logger.info("redis_client_rebuilt", reason="event_loop_changed")
        stale, _redis_client, _client_loop = _redis_client, None, None
        try:
            await stale.aclose()
        except Exception:
            # The old loop is gone, so closing may itself fail. The pool is
            # unreachable either way; dropping the reference is what matters.
            pass

    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20,
            # Every caller degrades gracefully without Redis, but only once the
            # call fails. With no timeout an unreachable host stalls login, the
            # rate limiter and /health/ready for the OS TCP timeout instead.
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        _client_loop = loop

    return _redis_client


async def close_redis() -> None:
    """Close the Redis connection."""
    global _redis_client, _client_loop
    if _redis_client is not None:
        await _redis_client.aclose()
    _redis_client = None
    _client_loop = None
