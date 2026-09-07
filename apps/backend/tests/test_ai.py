"""Tests for AI module — tailored resume, auto apply, matching."""
from __future__ import annotations

import os

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import JobModel, ResumeModel

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


# ── Provider error reporting ────────────────────────────────────────────────

def test_retired_model_is_reported_as_such():
    """A retired model returns an opaque 410; "provider failed" is not actionable."""
    from modules.ai.application.llm_service import _explain

    message = _explain(
        "nvidia_nim",
        "generate",
        Exception("Error code: 410 - the model has reached its end of life"),
    )
    assert "descontinuado" in message
    assert "Configurações" in message


def test_rejected_key_is_distinguished_from_other_failures():
    from modules.ai.application.llm_service import _explain

    assert "recusada" in _explain("openai", "generate", Exception("Error code: 401"))
    assert "limitando" in _explain("openai", "generate", Exception("Error code: 429"))
    assert "não respondeu" in _explain("openai", "generate", Exception("Request timed out"))


def test_unknown_failures_keep_their_detail():
    from modules.ai.application.llm_service import _explain

    message = _explain("openai", "compare_job", Exception("connection reset"))
    assert "connection reset" in message
    assert "compare_job" in message


def test_nvidia_model_comes_from_settings():
    """The default lived in two places and they had already drifted apart."""
    from core.config import settings
    from modules.ai.infrastructure.providers.factory import LLMProviderFactory

    provider = LLMProviderFactory.create("nvidia_nim", api_key="test")
    assert provider.model == settings.NVIDIA_NIM_MODEL

    override = LLMProviderFactory.create("nvidia_nim", api_key="test", model="other/model")
    assert override.model == "other/model"
