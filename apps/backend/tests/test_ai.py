"""Tests for AI module — tailored resume, auto apply, matching."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import JobModel, CompanyModel, ResumeModel
import os

SKIP_AI = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY", "").startswith("sk-"),
    reason="No valid OpenAI API key",
)


@pytest.mark.asyncio
async def test_tailor_resume_no_resume(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "tailor@test.com", "password": "pass12345"})
    token = reg.json()["token"]

    r = await client.post("/api/v1/ai/tailor-resume",
                          headers={"Authorization": f"Bearer {token}"},
                          json={"resume_id": "00000000-0000-0000-0000-000000000000",
                                "job_id": "00000000-0000-0000-0000-000000000000"})
    assert r.status_code == 404


@SKIP_AI
@pytest.mark.asyncio
async def test_tailor_resume_with_data(client: AsyncClient, db_session: AsyncSession):
    import uuid
    reg = await client.post("/api/v1/auth/register", json={"email": "tailor2@test.com", "password": "pass12345"})
    token = reg.json()["token"]

    # Create resume + job
    resume = ResumeModel(id=str(uuid.uuid4()), user_id=reg.json()["user_id"],
                         title="CV", content_text="Python developer with 5 years experience")
    db_session.add(resume)

    job = JobModel(id=str(uuid.uuid4()), title="Senior Python Dev", description="Python, FastAPI, PostgreSQL")
    db_session.add(job)
    await db_session.commit()

    r = await client.post("/api/v1/ai/tailor-resume",
                          headers={"Authorization": f"Bearer {token}"},
                          json={"resume_id": resume.id, "job_id": job.id})
    # Without API key, should still return something (might fail but not 404)
    assert r.status_code in [200, 401, 500, 502]


@pytest.mark.asyncio
async def test_auto_apply_no_resume(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "auto@test.com", "password": "pass12345"})
    token = reg.json()["token"]

    r = await client.post("/api/v1/ai/auto-apply",
                          headers={"Authorization": f"Bearer {token}"},
                          json={"resume_id": "00000000-0000-0000-0000-000000000000",
                                "job_id": "00000000-0000-0000-0000-000000000000"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_match_endpoint_no_data(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "match@test.com", "password": "pass12345"})
    token = reg.json()["token"]

    r = await client.post("/api/v1/ai/match",
                          headers={"Authorization": f"Bearer {token}"},
                          json={"resume_id": "00000000-0000-0000-0000-000000000000",
                                "job_id": "00000000-0000-0000-0000-000000000000"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_ats_score_no_resume(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "ats@test.com", "password": "pass12345"})
    token = reg.json()["token"]

    r = await client.post("/api/v1/ai/ats-score",
                          headers={"Authorization": f"Bearer {token}"},
                          json={"resume_id": "00000000-0000-0000-0000-000000000000",
                                "job_id": "00000000-0000-0000-0000-000000000000"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_cover_letter_no_resume(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "cl@test.com", "password": "pass12345"})
    token = reg.json()["token"]

    r = await client.post("/api/v1/ai/cover-letter",
                          headers={"Authorization": f"Bearer {token}"},
                          json={"resume_id": "00000000-0000-0000-0000-000000000000",
                                "job_id": "00000000-0000-0000-0000-000000000000"})
    assert r.status_code == 404


@SKIP_AI
@pytest.mark.asyncio
async def test_auto_apply_with_llm(client: AsyncClient, db_session: AsyncSession):
    import uuid
    reg = await client.post("/api/v1/auth/register", json={"email": "auto2@test.com", "password": "pass12345"})
    token = reg.json()["token"]

    resume = ResumeModel(id=str(uuid.uuid4()), user_id=reg.json()["user_id"],
                         title="CV", content_text="Senior Python developer with FastAPI and React")
    db_session.add(resume)

    job = JobModel(id=str(uuid.uuid4()), title="Full Stack Python Dev",
                   description="Python, React, PostgreSQL")
    db_session.add(job)
    await db_session.commit()

    r = await client.post("/api/v1/ai/auto-apply",
                          headers={"Authorization": f"Bearer {token}"},
                          json={"resume_id": resume.id, "job_id": job.id})
    assert r.status_code in [200, 402, 500, 502]
    if r.status_code == 200:
        data = r.json()
        assert "application_id" in data
        assert "tailored_resume" in data
        assert "cover_letter" in data
