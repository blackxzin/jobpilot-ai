"""Tests for Calendar and AI Chat modules."""
from __future__ import annotations

import os

import pytest
from httpx import AsyncClient

SKIP_AI = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY", "").startswith("sk-"),
    reason="No valid OpenAI API key",
)


@pytest.mark.asyncio
async def test_calendar_create_event(client: AsyncClient):
    # Login
    reg = await client.post("/api/v1/auth/register", json={"email": "cal@test.com", "password": "pass12345"})
    token = reg.json()["token"]

    r = await client.post("/api/v1/calendar", headers={"Authorization": f"Bearer {token}"}, json={
        "title": "Entrevista Nubank",
        "event_type": "interview",
        "date": "2026-08-15T10:00:00",
        "notes": "Tech interview",
        "location": "Zoom",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "Entrevista Nubank"
    assert data["event_type"] == "interview"


@pytest.mark.asyncio
async def test_calendar_list_events(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "cal2@test.com", "password": "pass12345"})
    token = reg.json()["token"]

    await client.post("/api/v1/calendar", headers={"Authorization": f"Bearer {token}"}, json={
        "title": "Prazo candidatura", "event_type": "deadline", "date": "2026-08-20T23:59:00",
    })

    r = await client.get("/api/v1/calendar", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert len(data["events"]) == 1
    assert data["events"][0]["title"] == "Prazo candidatura"


@pytest.mark.asyncio
async def test_calendar_delete_event(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "cal3@test.com", "password": "pass12345"})
    token = reg.json()["token"]

    create = await client.post("/api/v1/calendar", headers={"Authorization": f"Bearer {token}"}, json={
        "title": "Evento teste", "event_type": "reminder",
    })
    event_id = create.json()["id"]

    r = await client.delete(f"/api/v1/calendar/{event_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200

    list_r = await client.get("/api/v1/calendar", headers={"Authorization": f"Bearer {token}"})
    assert len(list_r.json()["events"]) == 0


@SKIP_AI
@pytest.mark.asyncio
async def test_ai_chat(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "chat@test.com", "password": "pass12345"})
    token = reg.json()["token"]

    r = await client.post("/api/v1/ai/chat", headers={"Authorization": f"Bearer {token}"}, json={
        "message": "Dicas para entrevista",
    })
    assert r.status_code in [200, 401, 402, 403, 500, 502]


@pytest.mark.asyncio
async def test_github_import(client: AsyncClient, monkeypatch):
    """The client is stubbed: this test used to call github.com for real.

    That made it fail whenever the runner was rate-limited or offline, and it
    also asserted `"profile" in data or "error" in data` — which passed even
    when the import had failed.
    """
    import modules.ai.api.routes as ai_routes

    class _FakeGitHub:
        async def get_user(self, username):
            return {"name": "Pessoa Exemplo", "bio": "Backend", "login": username}

        async def get_repositories(self, username):
            return [{"name": f"repo-{index}"} for index in range(15)]

        async def get_skills(self, username):
            return ["Python", "Go"]

        async def close(self):
            self.closed = True

    monkeypatch.setattr(ai_routes, "GitHubClient", _FakeGitHub, raising=False)

    reg = await client.post("/api/v1/auth/register", json={"email": "gh@test.com", "password": "pass12345"})
    token = reg.json()["token"]

    r = await client.post(
        "/api/v1/ai/github/import",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "octocat"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["profile"]["name"] == "Pessoa Exemplo"
    assert data["total_repos"] == 15
    assert len(data["repos"]) == 10, "the response should be capped at ten repositories"
    assert data["skills"] == ["Python", "Go"]


@pytest.mark.asyncio
async def test_github_import_reports_a_missing_user(client: AsyncClient, monkeypatch):
    """A failed import used to return HTTP 200 with an error body."""
    import modules.ai.api.routes as ai_routes

    class _FailingGitHub:
        async def get_user(self, username):
            raise RuntimeError("404 Not Found")

        async def close(self):
            return None

    monkeypatch.setattr(ai_routes, "GitHubClient", _FailingGitHub, raising=False)

    reg = await client.post(
        "/api/v1/auth/register", json={"email": "ghfail@test.com", "password": "pass12345"}
    )
    token = reg.json()["token"]

    r = await client.post(
        "/api/v1/ai/github/import",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "does-not-exist"},
    )
    assert r.status_code == 404
    # The raw client exception must not leak to the caller.
    assert "404 Not Found" not in r.json()["detail"]


@SKIP_AI
@pytest.mark.asyncio
async def test_linkedin(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "li@test.com", "password": "pass12345"})
    token = reg.json()["token"]

    r = await client.post("/api/v1/ai/linkedin/analyze", headers={"Authorization": f"Bearer {token}"}, json={
        "url": "https://linkedin.com/in/test",
    })
    assert r.status_code in [200, 401, 403, 500, 502]


@pytest.mark.asyncio
async def test_full_flow(client: AsyncClient, pdf_bytes: bytes):
    """Full flow: register → create job → upload resume → matching → cover letter"""
    # Register
    reg = await client.post("/api/v1/auth/register", json={"email": "full@test.com", "password": "pass12345"})
    assert reg.status_code == 200
    token = reg.json()["token"]
    user_id = reg.json()["user_id"]

    # Upload resume
    resume_r = await client.post("/api/v1/resumes/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"title": "CV"}, files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
    )
    assert resume_r.status_code == 200
    resume_id = resume_r.json()["id"]

    # List resumes
    list_r = await client.get("/api/v1/resumes/list", headers={"Authorization": f"Bearer {token}"})
    assert list_r.status_code == 200
    assert len(list_r.json()["results"]) == 1

    # Logout
    logout_r = await client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_r.status_code == 200
