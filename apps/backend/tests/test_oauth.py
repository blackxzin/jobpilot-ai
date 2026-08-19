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
