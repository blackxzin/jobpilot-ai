"""Applications API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.exceptions import NotFoundError
from modules.auth.infrastructure.repositories import SQLAlchemyUserRepository, SQLAlchemySessionRepository
from modules.auth.application.use_cases import GetCurrentUserUseCase
from modules.applications.infrastructure.repositories import SQLAlchemyApplicationRepository
from modules.applications.application.use_cases import (
    CreateApplicationUseCase, UpdateApplicationStatusUseCase,
    GetUserApplicationsUseCase, GetApplicationStatsUseCase,
)
from modules.applications.application.use_cases import CreateApplicationDTO, UpdateStatusDTO
from modules.applications.domain.enums import ApplicationStatus

router = APIRouter(prefix="/applications", tags=["applications"])


class CreateAppRequest(BaseModel):
    job_id: str
    resume_id: str
    cover_letter: str = ""
    custom_message: str = ""
    source_platform: str = ""


class UpdateStatusRequest(BaseModel):
    status: str


@router.post("")
async def create_application(body: CreateAppRequest, authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    user = await auth_uc.execute(token)

    from uuid import UUID
    dto = CreateApplicationDTO(
        job_id=UUID(body.job_id),
        resume_id=UUID(body.resume_id),
        user_id=user.id,
        cover_letter=body.cover_letter,
        custom_message=body.custom_message,
        source_platform=body.source_platform,
    )
    use_case = CreateApplicationUseCase(SQLAlchemyApplicationRepository(db))
    app = await use_case.execute(dto)
    return _app_to_dict(app)


@router.get("/list")
async def list_applications(
    status: str = "", source: str = "",
    authorization: str = Header(""),
    db: AsyncSession = Depends(get_db),
):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    user = await auth_uc.execute(token)

    use_case = GetUserApplicationsUseCase(SQLAlchemyApplicationRepository(db))
    apps = await use_case.execute(user_id=str(user.id), status=status or None, source_platform=source or None)
    return {"results": [_app_to_dict(a) for a in apps]}


@router.get("/stats")
async def application_stats(authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    user = await auth_uc.execute(token)

    use_case = GetApplicationStatsUseCase(SQLAlchemyApplicationRepository(db))
    stats = await use_case.execute(user_id=str(user.id))
    return {"total": stats.total, "by_status": stats.by_status}


@router.patch("/{app_id}/status")
async def update_status(app_id: str, body: UpdateStatusRequest, authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    await auth_uc.execute(token)

    status_enum = ApplicationStatus(body.status)
    dto = UpdateStatusDTO(status=status_enum)
    use_case = UpdateApplicationStatusUseCase(SQLAlchemyApplicationRepository(db))
    app = await use_case.execute(app_id, dto)
    return _app_to_dict(app)


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
