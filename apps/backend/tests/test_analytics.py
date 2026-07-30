"""Tests for analytics module."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import UserModel, JobModel, CompanyModel, ApplicationModel, ResumeModel
from core.database import Base


@pytest.mark.asyncio
async def test_analytics_overview(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "analytics@test.com", "password": "pass12345"})
    assert reg.status_code == 200
    token = reg.json()["token"]

    r = await client.get("/api/v1/analytics/overview", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert "total_applications" in data
    assert "interview_rate" in data
    assert "offer_rate" in data
    assert "rejection_rate" in data
    assert "response_rate" in data
    assert "top_companies" in data
    assert "applications_over_time" in data


@pytest.mark.asyncio
async def test_analytics_with_data(client: AsyncClient, db_session: AsyncSession):
    import uuid
    from datetime import datetime, UTC

    reg = await client.post("/api/v1/auth/register", json={"email": "adata@test.com", "password": "pass12345"})
    token = reg.json()["token"]
    user_id = reg.json()["user_id"]

    # Create company + job + application to generate data
    company = CompanyModel(id=str(uuid.uuid4()), name="TechCorp")
    db_session.add(company)
    await db_session.flush()

    job = JobModel(id=str(uuid.uuid4()), title="Dev", company_id=company.id)
    db_session.add(job)
    await db_session.flush()

    app = ApplicationModel(
        id=str(uuid.uuid4()), user_id=user_id, job_id=job.id,
        resume_id=str(uuid.uuid4()), status="applied",
    )
    db_session.add(app)
    await db_session.commit()

    r = await client.get("/api/v1/analytics/overview", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["total_applications"] == 1
    assert data["top_companies"][0]["name"] == "TechCorp"
