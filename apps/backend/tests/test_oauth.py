"""Tests for OAuth routes (LinkedIn)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_linkedin_login_returns_auth_url(client: AsyncClient):
    """GET /auth/linkedin/login should return an auth_url."""
    r = await client.get("/api/v1/auth/linkedin/login")
    assert r.status_code == 200
    data = r.json()
    assert "auth_url" in data
    assert data["auth_url"].startswith("https://www.linkedin.com/oauth/v2/authorization")


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
