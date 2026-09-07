"""Tests for OAuth routes (LinkedIn)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_linkedin_login_returns_auth_url(client: AsyncClient, monkeypatch):
    """GET /auth/linkedin/login should return an auth_url when configured."""
    from core.config import settings

    monkeypatch.setattr(settings, "LINKEDIN_CLIENT_ID", "test-client-id")
    monkeypatch.setattr(settings, "LINKEDIN_CLIENT_SECRET", "test-client-secret")

    r = await client.get("/api/v1/auth/linkedin/login")
    assert r.status_code == 200
    data = r.json()
    assert "auth_url" in data
    assert data["auth_url"].startswith("https://www.linkedin.com/oauth/v2/authorization")
    assert "client_id=test-client-id" in data["auth_url"]


@pytest.mark.asyncio
async def test_linkedin_login_unconfigured_returns_503(client: AsyncClient, monkeypatch):
    """Without credentials the endpoint must not hand out a broken auth_url."""
    from core.config import settings

    monkeypatch.setattr(settings, "LINKEDIN_CLIENT_ID", "")
    monkeypatch.setattr(settings, "LINKEDIN_CLIENT_SECRET", "")

    r = await client.get("/api/v1/auth/linkedin/login")
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_linkedin_callback_missing_code(client: AsyncClient):
    """Callback without code should fail."""
    r = await client.get("/api/v1/auth/linkedin/callback?error=access_denied")
    assert r.status_code in [401, 422]


@pytest.mark.asyncio
async def test_linkedin_callback_invalid_state(client: AsyncClient):
    """Callback with invalid state should fail."""
    r = await client.get("/api/v1/auth/linkedin/callback?code=test&state=invalid")
    assert r.status_code == 401


# ── OAuth state storage ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_state_round_trips_and_is_single_use():
    """A replayed state must not authenticate a second session."""
    from modules.auth.infrastructure.oauth_state import (
        consume_state,
        reset_local_state,
        store_state,
    )

    reset_local_state()
    await store_state("state-abc", "/dashboard")

    assert await consume_state("state-abc") == "/dashboard"
    assert await consume_state("state-abc") is None


@pytest.mark.asyncio
async def test_unknown_state_is_rejected():
    from modules.auth.infrastructure.oauth_state import consume_state, reset_local_state

    reset_local_state()
    assert await consume_state("never-issued") is None
    assert await consume_state("") is None


@pytest.mark.asyncio
async def test_local_fallback_is_bounded(monkeypatch):
    """The fallback dictionary is attacker-driven, so it must not grow forever."""
    import modules.auth.infrastructure.oauth_state as module

    module.reset_local_state()
    # Force the fallback path by making the Redis lookup fail.
    monkeypatch.setattr(
        "core.redis_client.get_redis",
        lambda: (_ for _ in ()).throw(RuntimeError("redis down")),
    )
    monkeypatch.setattr(module, "MAX_LOCAL_STATES", 3)

    for index in range(3):
        await module.store_state(f"state-{index}", "/")

    with pytest.raises(RuntimeError):
        await module.store_state("state-overflow", "/")

    assert await module.pending_count() == 3
    module.reset_local_state()


@pytest.mark.asyncio
async def test_expired_local_state_is_dropped(monkeypatch):
    import modules.auth.infrastructure.oauth_state as module

    module.reset_local_state()
    monkeypatch.setattr(
        "core.redis_client.get_redis",
        lambda: (_ for _ in ()).throw(RuntimeError("redis down")),
    )
    await module.store_state("stale", "/")

    # Advance past the TTL rather than sleeping through it.
    monkeypatch.setattr(module.time, "monotonic", lambda: 1e9)
    assert await module.consume_state("stale") is None
    module.reset_local_state()
