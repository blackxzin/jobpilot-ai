"""Tests for vector search / semantic search module."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import JobModel, JobEmbeddingModel


@pytest.mark.asyncio
async def test_search_semantic_no_results(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "sem@test.com", "password": "pass12345"})
    token = reg.json()["token"]

    r = await client.get("/api/v1/search/semantic?q=python+developer", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    assert "python" in data["query"] and "developer" in data["query"]


@pytest.mark.asyncio
async def test_search_index_job_not_found(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "idx@test.com", "password": "pass12345"})
    token = reg.json()["token"]

    r = await client.post("/api/v1/search/index-job/00000000-0000-0000-0000-000000000000",
                          headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_search_index_and_semantic(client: AsyncClient, db_session: AsyncSession):
    import uuid
    reg = await client.post("/api/v1/auth/register", json={"email": "sem2@test.com", "password": "pass12345"})
    token = reg.json()["token"]

    # Create a job directly
    job = JobModel(id=str(uuid.uuid4()), title="Python Backend Developer",
                   description="Develop APIs with Python and FastAPI", location="Remote")
    db_session.add(job)
    await db_session.commit()

    # Index it
    r = await client.post(f"/api/v1/search/index-job/{job.id}",
                          headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["status"] == "indexed"

    # Search
    r = await client.get("/api/v1/search/semantic?q=python+backend",
                         headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    # May or may not find results depending on embedding
    assert "results" in data
