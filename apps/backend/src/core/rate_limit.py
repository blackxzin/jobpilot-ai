"""Fixed-window rate limiting for abuse-prone endpoints.

Login and registration are the two routes an attacker can hammer for free:
one to guess passwords, the other to enumerate which emails exist. Redis backs
the counter when available so limits hold across backend replicas, with an
in-process fallback that still protects a single-instance deployment.
"""
from __future__ import annotations

import time
from collections import defaultdict

from core.exceptions import JobPilotException
from core.logger import get_logger

logger = get_logger(__name__)

# request timestamps per key, used only when Redis is unreachable
_local_hits: dict[str, list[float]] = defaultdict(list)
_LOCAL_MAX_KEYS = 10_000


class RateLimitExceeded(JobPilotException):
    """Too many requests for this key within the window."""


def _client_key(request, scope: str) -> str:
    client_host = request.client.host if request.client else "unknown"
    # Behind a proxy the socket address is the proxy's, so prefer the
    # forwarded chain's first hop when the deployment sets one.
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        client_host = forwarded.split(",")[0].strip()
    return f"ratelimit:{scope}:{client_host}"


async def enforce_rate_limit(request, scope: str, limit: int, window_seconds: int) -> None:
    """Raise RateLimitExceeded when `scope` exceeds `limit` in the window."""
    from core.config import settings

    if not settings.RATE_LIMIT_ENABLED:
        return

    key = _client_key(request, scope)

    try:
        from core.redis_client import get_redis

        redis = await get_redis()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)
        if count > limit:
            raise RateLimitExceeded("Muitas tentativas. Tente novamente em alguns minutos.")
        return
    except RateLimitExceeded:
        raise
    except Exception as e:
        logger.warning("rate_limit_redis_unavailable_using_local", error=str(e))

    _enforce_locally(key, limit, window_seconds)


def _enforce_locally(key: str, limit: int, window_seconds: int) -> None:
    now = time.monotonic()
    cutoff = now - window_seconds

    if len(_local_hits) > _LOCAL_MAX_KEYS:
        # Unbounded growth would be a memory leak an attacker controls.
        _local_hits.clear()

    hits = [t for t in _local_hits[key] if t > cutoff]
    hits.append(now)
    _local_hits[key] = hits

    if len(hits) > limit:
        raise RateLimitExceeded("Muitas tentativas. Tente novamente em alguns minutos.")


def reset_local_state() -> None:
    """Clear the in-process counters. Used by tests."""
    _local_hits.clear()
