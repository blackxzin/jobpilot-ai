"""Applications API routes."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.exceptions import NotFoundError, ValidationError
from modules.applications.application.use_cases import (
    CreateApplicationDTO,
    CreateApplicationUseCase,
    GetApplicationStatsUseCase,
    UpdateApplicationStatusUseCase,
    UpdateStatusDTO,
)
from modules.applications.domain.enums import ApplicationStatus
from modules.applications.infrastructure.repositories import SQLAlchemyApplicationRepository
from modules.auth.api.dependencies import ensure_owner, get_current_user
from modules.auth.domain.entities import User

router = APIRouter(prefix="/applications", tags=["applications"])


class CreateAppRequest(BaseModel):
    job_id: str
    resume_id: str
    cover_letter: str = ""
    custom_message: str = ""
    source_platform: str = ""


class UpdateStatusRequest(BaseModel):
    status: str


def _parse_uuid(value: str, field: str) -> UUID:
    """Parse a UUID string, surfacing a 422 instead of a 500 on bad input."""
    try:
        return UUID(value)
    except (ValueError, AttributeError, TypeError) as e:
        raise ValidationError(f"{field} must be a valid UUID") from e


@router.post("")
async def create_application(
    body: CreateAppRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    dto = CreateApplicationDTO(
        job_id=_parse_uuid(body.job_id, "job_id"),
        resume_id=_parse_uuid(body.resume_id, "resume_id"),
        user_id=user.id,
        cover_letter=body.cover_letter,
        custom_message=body.custom_message,
        source_platform=body.source_platform,
    )
    use_case = CreateApplicationUseCase(SQLAlchemyApplicationRepository(db))
    application = await use_case.execute(dto)
    return _app_to_dict(application)


@router.get("/list")
async def list_applications(
    status: str = "",
    source: str = "",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repository = SQLAlchemyApplicationRepository(db)
    rows = await repository.get_for_user_with_job(str(user.id))

    results = [
        {**_app_to_dict(application), "job_title": job_title, "company": company}
        for application, job_title, company in rows
        if (not status or _status_value(application.status) == status)
        and (not source or application.source_platform == source)
    ]
    return {"results": results}


def _status_value(status) -> str:
    return status.value if hasattr(status, "value") else str(status)


@router.get("/stats")
async def application_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    use_case = GetApplicationStatsUseCase(SQLAlchemyApplicationRepository(db))
    stats = await use_case.execute(user_id=str(user.id))
    return {"total": stats.total, "by_status": stats.by_status}


@router.patch("/{app_id}/status")
async def update_status(
    app_id: str,
    body: UpdateStatusRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        status_enum = ApplicationStatus(body.status)
    except ValueError as e:
        raise ValidationError(
            f"Invalid status '{body.status}'. Allowed: {', '.join(ApplicationStatus.all_values())}"
        ) from e

    repository = SQLAlchemyApplicationRepository(db)
    existing = await repository.get_by_id(app_id)
    if existing is None:
        raise NotFoundError("Application not found")
    ensure_owner(existing.user_id, user, "Application")

    use_case = UpdateApplicationStatusUseCase(repository)
    application = await use_case.execute(app_id, UpdateStatusDTO(status=status_enum))
    return _app_to_dict(application)


def _app_to_dict(a) -> dict:
    return {
        "id": str(a.id),
        "job_id": str(a.job_id),
        "resume_id": str(a.resume_id),
        "status": a.status.value if hasattr(a.status, "value") else a.status,
        "cover_letter": (a.cover_letter or "")[:100],
        "source_platform": a.source_platform,
        "applied_at": str(a.applied_at) if a.applied_at else None,
        "responded_at": str(a.responded_at) if a.responded_at else None,
        "created_at": str(a.created_at),
    }
