"""Resume API routes — upload, list, get."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.exceptions import NotFoundError
from modules.auth.infrastructure.repositories import SQLAlchemyUserRepository, SQLAlchemySessionRepository
from modules.auth.application.use_cases import GetCurrentUserUseCase
from modules.resume.application.use_cases import UploadResumeUseCase, GetResumeUseCase, ListResumesUseCase
from modules.resume.infrastructure.repositories import ResumeRepository

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/upload")
async def upload_resume(
    title: str = Form("My Resume"),
    file: UploadFile = File(...),
    authorization: str = Header(""),
    db: AsyncSession = Depends(get_db),
):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    user = await auth_uc.execute(token)

    content = await file.read()
    use_case = UploadResumeUseCase(ResumeRepository(db))
    result = await use_case.execute(user_id=str(user.id), title=title, file_content=content, filename=file.filename or "resume.pdf")
    return result


@router.get("/list")
async def list_resumes(authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    user = await auth_uc.execute(token)

    use_case = ListResumesUseCase(ResumeRepository(db))
    results = await use_case.execute(user_id=str(user.id))
    return {"results": [_r_to_dict(r) for r in results]}


@router.get("/{resume_id}")
async def get_resume(resume_id: str, authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    await auth_uc.execute(token)

    use_case = GetResumeUseCase(ResumeRepository(db))
    result = await use_case.execute(resume_id)
    return _r_to_dict(result)


def _r_to_dict(r) -> dict:
    return {
        "id": r.id if not isinstance(r, dict) else r.get("id"),
        "title": r.title if not isinstance(r, dict) else r.get("title"),
        "file_url": r.file_url if not isinstance(r, dict) else r.get("file_url"),
        "content_preview": (r.content_text or "")[:200] if not isinstance(r, dict) else (r.get("content_text", "")[:200]),
        "ats_score": r.ats_score if not isinstance(r, dict) else r.get("ats_score"),
        "created_at": str(r.created_at) if not isinstance(r, dict) else r.get("created_at"),
    }
