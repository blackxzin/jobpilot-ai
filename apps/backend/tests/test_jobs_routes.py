"""Tests for the jobs routes.

External boards are stubbed: the point is how the API behaves when a board is
slow, broken or empty, not whether a third-party site is up today.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

import modules.jobs.api.routes as jobs_routes


async def _register(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "password1234"}
    )
    return response.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class _Board:
    def __init__(self, postings=None, fail=False):
        self._postings = postings or []
        self._fail = fail
        self.closed = False

    async def search_jobs(self, **_kwargs):
        if self._fail:
            raise RuntimeError("board unreachable")
        return self._postings

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_job_routes_require_a_session(client: AsyncClient):
    """These proxy third-party boards; open, they burn our rate limits for free."""
    for path in ("/api/v1/jobs", "/api/v1/jobs/remoteok", "/api/v1/jobs/search-all"):
        assert (await client.get(path)).status_code == 401


@pytest.mark.asyncio
async def test_creating_a_job_then_finding_it_locally(client: AsyncClient):
    token = await _register(client, "createjob@test.com")

    created = await client.post(
        "/api/v1/jobs",
        headers=_auth(token),
        json={
            "title": "Engenheira de Plataforma",
            "company_name": "Acme",
            "description": "Kubernetes e Terraform",
            "is_remote": True,
        },
    )
    assert created.status_code == 200
    assert created.json()["company"] == "Acme"

    found = await client.get("/api/v1/jobs?query=Plataforma", headers=_auth(token))
    assert [job["title"] for job in found.json()["results"]] == ["Engenheira de Plataforma"]


@pytest.mark.asyncio
async def test_job_detail_validates_the_identifier(client: AsyncClient):
    token = await _register(client, "jobdetail@test.com")

    assert (await client.get("/api/v1/jobs/not-a-uuid", headers=_auth(token))).status_code == 422

    import uuid

    missing = await client.get(f"/api/v1/jobs/{uuid.uuid4()}", headers=_auth(token))
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_an_unreachable_board_is_reported_as_unavailable(
    client: AsyncClient, monkeypatch
):
    """"No results" and "the board is down" must not look the same to the UI."""
    board = _Board(fail=True)
    monkeypatch.setattr(jobs_routes, "RemoteOKClient", lambda: board)

    token = await _register(client, "boarddown@test.com")
    response = await client.get("/api/v1/jobs/remoteok?q=python", headers=_auth(token))

    assert response.status_code == 200
    assert response.json() == {"results": [], "source": "remoteok", "available": False}
    assert board.closed, "the HTTP client was leaked"


@pytest.mark.asyncio
async def test_a_working_board_returns_its_postings(client: AsyncClient, monkeypatch):
    posting = {"title": "Backend Engineer", "company": "Acme", "url": "https://example.com"}
    monkeypatch.setattr(jobs_routes, "RemoteOKClient", lambda: _Board([posting]))

    token = await _register(client, "boardup@test.com")
    body = (await client.get("/api/v1/jobs/remoteok?q=python", headers=_auth(token))).json()

    assert body["available"] is True
    assert body["results"] == [posting]


@pytest.mark.asyncio
async def test_search_all_names_the_boards_that_failed(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(jobs_routes, "RemoteOKClient", lambda: _Board([{"title": "A"}]))
    monkeypatch.setattr(jobs_routes, "JobicyClient", lambda: _Board(fail=True))
    monkeypatch.setattr(jobs_routes, "GoogleJobsClient", lambda: _Board(fail=True))

    token = await _register(client, "searchall@test.com")
    body = (await client.get("/api/v1/jobs/search-all?q=python", headers=_auth(token))).json()

    assert [group["source"] for group in body["results"]] == ["remoteok"]
    assert set(body["unavailable_sources"]) == {"jobicy", "google_jobs"}


@pytest.mark.asyncio
async def test_creating_a_job_requires_a_title_and_company(client: AsyncClient):
    token = await _register(client, "badjob@test.com")
    response = await client.post(
        "/api/v1/jobs", headers=_auth(token), json={"title": "", "company_name": ""}
    )
    assert response.status_code == 422
