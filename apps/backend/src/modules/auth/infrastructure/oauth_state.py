"""Storage for in-flight OAuth state tokens.

The state token ties a callback back to the browser that started the flow; if
it can't be found, the callback is rejected. Keeping it in a process
dictionary meant the flow only worked when the callback happened to land on
the same backend replica that issued it — so OAuth broke as soon as the
deployment scaled past one instance, intermittently and only in production.

Redis is the primary store. The in-process fallback keeps single-instance and
test runs working when Redis is unavailable.
"""
from __future__ import annotations

import time

from core.logger import get_logger

logger = get_logger(__name__)

STATE_TTL_SECONDS = 600
MAX_LOCAL_STATES = 1000
_KEY_PREFIX = "oauth:state:"

# state -> (redirect target, issued at). Fallback only.
_local: dict[str, tuple[str, float]] = {}


def _purge_local(now: float) -> None:
    expired = [key for key, (_, issued) in _local.items() if now - issued > STATE_TTL_SECONDS]
    for key in expired:
        _local.pop(key, None)


async def store_state(state: str, redirect: str) -> None:
    """Record a pending OAuth flow, expiring on its own after the TTL."""
    try:
        from core.redis_client import get_redis

        redis = await get_redis()
        await redis.set(f"{_KEY_PREFIX}{state}", redirect, ex=STATE_TTL_SECONDS)
        return
    except Exception as e:
        logger.warning("oauth_state_redis_unavailable_using_local", error=str(e))

    now = time.monotonic()
    _purge_local(now)
    if len(_local) >= MAX_LOCAL_STATES:
        raise RuntimeError("Too many pending OAuth flows")
    _local[state] = (redirect, now)


async def consume_state(state: str) -> str | None:
    """Return the redirect for `state` and invalidate it.

    One-time use: a replayed state must not authenticate a second session.
    """
    if not state:
        return None

    try:
        from core.redis_client import get_redis

        redis = await get_redis()
        key = f"{_KEY_PREFIX}{state}"
        # GETDEL is atomic, so two concurrent callbacks cannot both succeed.
        redirect = await redis.getdel(key)
        if redirect is not None:
            return redirect
    except Exception as e:
        logger.warning("oauth_state_redis_unavailable_using_local", error=str(e))

    now = time.monotonic()
    _purge_local(now)
    entry = _local.pop(state, None)
    return entry[0] if entry else None


async def pending_count() -> int:
    """Number of flows waiting in the local fallback. Used by tests."""
    _purge_local(time.monotonic())
    return len(_local)


def reset_local_state() -> None:
    """Clear the in-process fallback. Used by tests."""
    _local.clear()
