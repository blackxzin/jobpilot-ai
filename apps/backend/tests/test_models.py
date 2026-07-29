"""Tests for SQLAlchemy models instantiation."""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import (
    UserModel, SessionModel, ResumeModel, JobModel, ApplicationModel,
    NotificationModel, CompanyModel, CoverLetterModel, AIAnalysisModel,
)


@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession):
    import uuid
    user = UserModel(id=str(uuid.uuid4()), email="test@test.com", hashed_password="hash")
    db_session.add(user)
    await db_session.commit()

    assert user.id is not None
    assert user.email == "test@test.com"


@pytest.mark.asyncio
async def test_create_job(db_session: AsyncSession):
    import uuid
    job = JobModel(id=str(uuid.uuid4()), title="Dev")
    db_session.add(job)
    await db_session.commit()

    assert job.id is not None
    assert job.title == "Dev"
    assert job.is_active is True
