"""Tests for the Redis client singleton.

A client's connection pool is bound to the event loop that created it. Reusing
it from another loop raises "Event loop is closed", and every caller silently
degrades to its fallback instead of using Redis — which is how an OAuth state
stored in Redis came back from the in-process dictionary instead.
"""
from __future__ import annotations

import asyncio

import pytest

import core.redis_client as redis_client


class _FakeRedis:
    instances: list[_FakeRedis] = []

    def __init__(self):
        self.closed = False
        _FakeRedis.instances.append(self)

    async def aclose(self):
        self.closed = True


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    _FakeRedis.instances.clear()
    monkeypatch.setattr(redis_client, "_redis_client", None)
    monkeypatch.setattr(redis_client, "_client_loop", None)
    monkeypatch.setattr(redis_client.aioredis, "from_url", lambda *a, **k: _FakeRedis())
    yield
    monkeypatch.setattr(redis_client, "_redis_client", None)
    monkeypatch.setattr(redis_client, "_client_loop", None)


@pytest.mark.asyncio
async def test_the_client_is_reused_within_one_loop():
    first = await redis_client.get_redis()
    second = await redis_client.get_redis()

    assert first is second
    assert len(_FakeRedis.instances) == 1


def test_a_new_loop_gets_a_new_client():
    """Each test runs on a fresh loop; the old client's pool is already dead."""
    first = asyncio.run(redis_client.get_redis())
    second = asyncio.run(redis_client.get_redis())

    assert first is not second
    assert first.closed, "the stale client should have been disposed"


def test_closing_a_stale_client_never_propagates():
    """The old loop is gone, so closing it can fail; that must not break callers."""

    class _Unclosable(_FakeRedis):
        async def aclose(self):
            raise RuntimeError("Event loop is closed")

    asyncio.run(redis_client.get_redis())
    redis_client._redis_client = _Unclosable()

    # Must not raise even though disposal fails.
    assert asyncio.run(redis_client.get_redis()) is not None


@pytest.mark.asyncio
async def test_close_clears_the_singleton():
    client = await redis_client.get_redis()
    await redis_client.close_redis()

    assert client.closed
    assert redis_client._redis_client is None
    assert await redis_client.get_redis() is not client
