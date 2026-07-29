"""Application module tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_application(client: AsyncClient):
    # Register user first
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "app@example.com", "password": "password123"},
    )
    token = reg.json()["token"]
    user_id = reg.json()["user_id"]

    # Create a job first
    from sqlalchemy.ext.asyncio import AsyncSession
    from core.database import get_db
    from core.models import JobModel
    import uuid

    # Access the db session through the app
    async for db in get_db():
        job = JobModel(
            id=str(uuid.uuid4()),
            title="Software Engineer",
            source="manual",
        )
        db.add(job)
        await db.commit()
        job_id = job.id
        break

    # Create a resume first
    from core.models import ResumeModel
    async for db in get_db():
        resume = ResumeModel(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title="My Resume",
            content_text="Test content",
        )
        db.add(resume)
        await db.commit()
        resume_id = resume.id
        break

    response = await client.post(
        "/api/v1/applications",
        headers={"Authorization": f"Bearer {token}"},
        json={"job_id": job_id, "resume_id": resume_id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "applied"


@pytest.mark.asyncio
async def test_list_applications(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "listapp@example.com", "password": "password123"},
    )
    token = reg.json()["token"]

    response = await client.get(
        "/api/v1/applications/list",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert "results" in response.json()
