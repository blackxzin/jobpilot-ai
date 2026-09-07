"""Tests for health probes and the LinkedIn OAuth callback.

The callback is the one route that trades a third-party code for a session, so
its failure modes matter more than its happy path.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

import modules.auth.api.routes as auth_routes
from core.config import settings


class _FakeResponse:
    def __init__(self, payload: dict, ok: bool = True):
        self._payload = payload
        self.is_success = ok

    def json(self) -> dict:
        return self._payload


class _FakeHttpClient:
    """Stands in for httpx.AsyncClient during the token exchange."""

    def __init__(self, token_response: _FakeResponse, profile_response: _FakeResponse):
        self._token = token_response
        self._profile = profile_response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def post(self, *_args, **_kwargs):
        return self._token

    async def get(self, *_args, **_kwargs):
        return self._profile


@pytest.fixture
def linkedin_configured(monkeypatch):
    monkeypatch.setattr(settings, "LINKEDIN_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "LINKEDIN_CLIENT_SECRET", "client-secret")


# ── Health ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_liveness_never_touches_a_dependency(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_readiness_reports_each_dependency(client: AsyncClient):
    """Routing traffic on liveness alone sends requests to a backend with no database."""
    response = await client.get("/health/ready")
    assert response.status_code in (200, 503)
    checks = response.json()["checks"]
    assert set(checks) == {"database", "redis"}


@pytest.mark.asyncio
async def test_metadata_advertises_instance_capabilities(client: AsyncClient):
    body = (await client.get("/api/v1/meta")).json()
    assert set(body) == {"version", "demo_mode", "linkedin_oauth"}


# ── OAuth callback ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_callback_rejects_an_unknown_state(client: AsyncClient, linkedin_configured):
    """The state ties the callback to the browser that started the flow."""
    response = await client.get("/api/v1/auth/linkedin/callback?code=abc&state=never-issued")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_callback_surfaces_a_provider_error(client: AsyncClient, linkedin_configured):
    response = await client.get("/api/v1/auth/linkedin/callback?error=access_denied")
    assert response.status_code == 401
    assert "access_denied" in response.json()["detail"]


@pytest.mark.asyncio
async def test_callback_requires_a_code(client: AsyncClient, linkedin_configured, monkeypatch):
    from modules.auth.infrastructure.oauth_state import reset_local_state, store_state

    reset_local_state()
    await store_state("valid-state", "/")

    response = await client.get("/api/v1/auth/linkedin/callback?state=valid-state")
    assert response.status_code == 401
    assert "code" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_callback_creates_a_session_and_redirects(
    client: AsyncClient, linkedin_configured, monkeypatch
):
    from modules.auth.infrastructure.oauth_state import reset_local_state, store_state

    reset_local_state()
    await store_state("good-state", "/")

    monkeypatch.setattr(
        auth_routes.httpx,
        "AsyncClient",
        lambda **_kwargs: _FakeHttpClient(
            _FakeResponse({"access_token": "linkedin-token"}),
            _FakeResponse(
                {
                    "sub": "linkedin-user-1",
                    "email": "oauth@example.com",
                    "name": "Pessoa Exemplo",
                }
            ),
        ),
    )

    response = await client.get("/api/v1/auth/linkedin/callback?code=abc&state=good-state")

    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith(settings.FRONTEND_URL.rstrip("/"))
    assert "token=" in location


@pytest.mark.asyncio
async def test_callback_fails_when_the_token_exchange_is_refused(
    client: AsyncClient, linkedin_configured, monkeypatch
):
    from modules.auth.infrastructure.oauth_state import reset_local_state, store_state

    reset_local_state()
    await store_state("refused-state", "/")

    monkeypatch.setattr(
        auth_routes.httpx,
        "AsyncClient",
        lambda **_kwargs: _FakeHttpClient(_FakeResponse({}, ok=False), _FakeResponse({})),
    )

    response = await client.get("/api/v1/auth/linkedin/callback?code=abc&state=refused-state")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_is_unavailable_when_oauth_is_not_configured(
    client: AsyncClient, monkeypatch
):
    """Without credentials the old code handed out a URL that could never work."""
    monkeypatch.setattr(settings, "LINKEDIN_CLIENT_ID", "")
    monkeypatch.setattr(settings, "LINKEDIN_CLIENT_SECRET", "")

    response = await client.get("/api/v1/auth/linkedin/login")
    assert response.status_code == 503
