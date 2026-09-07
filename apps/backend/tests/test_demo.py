"""Tests for demo seeding — the path a first-time user lands on."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.models import (
    ApplicationModel,
    CalendarEventModel,
    JobEmbeddingModel,
    JobModel,
    NotificationModel,
    ResumeModel,
    UserModel,
)


async def _seed(monkeypatch, db_session: AsyncSession) -> bool:
    """Run the seeder against the test session factory."""
    from contextlib import asynccontextmanager

    import core.demo as demo

    @asynccontextmanager
    async def _session_scope():
        yield db_session

    monkeypatch.setattr(demo, "get_session_factory", lambda: _session_scope)
    return await demo.seed_demo_data()


@pytest.mark.asyncio
async def test_seed_creates_a_usable_demo_account(monkeypatch, db_session: AsyncSession):
    assert await _seed(monkeypatch, db_session) is True

    user = (
        await db_session.execute(
            select(UserModel).where(UserModel.email == settings.DEMO_EMAIL)
        )
    ).scalar_one()
    assert user.full_name

    assert await db_session.scalar(select(func.count()).select_from(JobModel)) == 8
    assert await db_session.scalar(select(func.count()).select_from(ApplicationModel)) == 7
    assert await db_session.scalar(select(func.count()).select_from(CalendarEventModel)) == 4
    assert await db_session.scalar(select(func.count()).select_from(NotificationModel)) == 4

    resume = (
        await db_session.execute(select(ResumeModel).where(ResumeModel.user_id == user.id))
    ).scalar_one()
    assert resume.ats_score and resume.content_text


@pytest.mark.asyncio
async def test_seed_is_idempotent(monkeypatch, db_session: AsyncSession):
    """Restarting the stack must not duplicate the demo dataset."""
    assert await _seed(monkeypatch, db_session) is True
    assert await _seed(monkeypatch, db_session) is False
    assert await db_session.scalar(select(func.count()).select_from(JobModel)) == 8


@pytest.mark.asyncio
async def test_every_demo_job_is_indexed_for_semantic_search(
    monkeypatch, db_session: AsyncSession
):
    await _seed(monkeypatch, db_session)
    jobs = await db_session.scalar(select(func.count()).select_from(JobModel))
    embeddings = await db_session.scalar(select(func.count()).select_from(JobEmbeddingModel))
    assert embeddings == jobs


@pytest.mark.asyncio
async def test_demo_user_can_log_in_and_see_data(
    monkeypatch, client: AsyncClient, db_session: AsyncSession
):
    """End to end: the credentials printed by the seeder actually work."""
    await _seed(monkeypatch, db_session)

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": settings.DEMO_EMAIL, "password": settings.DEMO_PASSWORD},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    overview = await client.get("/api/v1/analytics/overview", headers=headers)
    assert overview.status_code == 200
    assert overview.json()["total_applications"] == 7
    assert overview.json()["offers"] == 1

    applications = await client.get("/api/v1/applications/list", headers=headers)
    assert len(applications.json()["results"]) == 7


@pytest.mark.asyncio
async def test_semantic_search_ranks_relevant_demo_jobs_first(
    monkeypatch, client: AsyncClient, db_session: AsyncSession
):
    """Search must return real matches with no embeddings API configured."""
    await _seed(monkeypatch, db_session)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": settings.DEMO_EMAIL, "password": settings.DEMO_PASSWORD},
    )
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    r = await client.get("/api/v1/search/semantic?q=kubernetes+terraform+go", headers=headers)
    assert r.status_code == 200
    results = r.json()["results"]
    assert results, "semantic search returned nothing for an indexed term"
    assert "Plataforma" in results[0]["title"]
    assert results[0]["score"] > 0
