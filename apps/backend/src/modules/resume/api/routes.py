"""Resume API routes — upload, list, get."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.exceptions import ValidationError
from modules.auth.api.dependencies import ensure_owner, get_current_user
from modules.auth.domain.entities import User
from modules.resume.application.use_cases import (
    GetResumeUseCase,
    ListResumesUseCase,
    UploadResumeUseCase,
)
from modules.resume.infrastructure.repositories import ResumeRepository

router = APIRouter(prefix="/resumes", tags=["resumes"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = (".pdf",)


@router.post("/upload")
async def upload_resume(
    title: str = Form("My Resume"),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filename = file.filename or "resume.pdf"
    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise ValidationError("Only PDF files are accepted")

    content = await file.read()
    if not content:
        raise ValidationError("Uploaded file is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValidationError(f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit")

    use_case = UploadResumeUseCase(ResumeRepository(db))
    return await use_case.execute(
        user_id=str(user.id), title=title, file_content=content, filename=filename
    )


@router.get("/list")
async def list_resumes(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    use_case = ListResumesUseCase(ResumeRepository(db))
    results = await use_case.execute(user_id=str(user.id))
    return {"results": [_r_to_dict(r) for r in results]}


@router.get("/{resume_id}")
async def get_resume(
    resume_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    use_case = GetResumeUseCase(ResumeRepository(db))
    resume = await use_case.execute(resume_id)
    ensure_owner(resume.user_id, user, "Resume")
    return _r_to_dict(resume)


def _r_to_dict(r) -> dict:
    return {
        "id": r.id if not isinstance(r, dict) else r.get("id"),
        "title": r.title if not isinstance(r, dict) else r.get("title"),
        "file_url": r.file_url if not isinstance(r, dict) else r.get("file_url"),
        "content_preview": (r.content_text or "")[:200] if not isinstance(r, dict) else (r.get("content_text", "")[:200]),
        "ats_score": r.ats_score if not isinstance(r, dict) else r.get("ats_score"),
        "created_at": str(r.created_at) if not isinstance(r, dict) else r.get("created_at"),
    }
