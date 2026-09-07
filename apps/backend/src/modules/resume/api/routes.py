"""Resume API routes — upload, list, get."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.exceptions import ValidationError
from core.logger import get_logger
from core.validators import validate_uuid
from modules.auth.api.dependencies import ensure_owner, get_current_user
from modules.auth.domain.entities import User
from modules.resume.application.use_cases import (
    GetResumeUseCase,
    ListResumesUseCase,
    UploadResumeUseCase,
)
from modules.resume.infrastructure.repositories import ResumeRepository

logger = get_logger(__name__)
router = APIRouter(prefix="/resumes", tags=["resumes"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
UPLOAD_CHUNK_BYTES = 64 * 1024
ALLOWED_EXTENSIONS = (".pdf",)
# Every PDF starts with this signature. Checking it stops a renamed
# executable or archive from reaching the parser.
PDF_MAGIC = b"%PDF-"


async def _read_limited(file: UploadFile) -> bytes:
    """Read an upload, aborting as soon as it exceeds the size limit.

    Reading the whole body first and checking the length afterwards means a
    multi-gigabyte upload is fully buffered in memory before being rejected.
    """
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(UPLOAD_CHUNK_BYTES):
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise ValidationError(
                f"Arquivo excede o limite de {MAX_UPLOAD_BYTES // (1024 * 1024)} MB"
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/upload")
async def upload_resume(
    title: str = Form("My Resume"),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filename = file.filename or "resume.pdf"
    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise ValidationError("Apenas arquivos PDF são aceitos")

    content = await _read_limited(file)
    if not content:
        raise ValidationError("O arquivo enviado está vazio")
    if not content.startswith(PDF_MAGIC):
        raise ValidationError("O arquivo não é um PDF válido")

    use_case = UploadResumeUseCase(ResumeRepository(db))
    resume = await use_case.execute(
        user_id=str(user.id), title=title, file_content=content, filename=filename
    )

    # Best-effort: the resume is saved either way, and the score is filled in
    # asynchronously. A broker that is down must not fail the upload.
    _queue_ats_scoring(str(resume.id))
    return _r_to_dict(resume)


def _queue_ats_scoring(resume_id: str) -> None:
    try:
        from workers.ats_scoring import score_resume

        score_resume.delay(resume_id)
    except Exception as e:
        logger.warning("ats_scoring_dispatch_failed", resume_id=resume_id, error=str(e))


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
    resume = await use_case.execute(validate_uuid(resume_id, "resume_id"))
    ensure_owner(resume.user_id, user, "Resume")
    return _r_to_dict(resume)


PREVIEW_CHARS = 200


def _r_to_dict(resume) -> dict:
    """Serialize a resume row for the API."""
    return {
        "id": str(resume.id),
        "title": resume.title or "",
        "file_url": resume.file_url or "",
        "content_preview": (resume.content_text or "")[:PREVIEW_CHARS],
        "ats_score": resume.ats_score,
        "ats_breakdown": resume.ats_breakdown or {},
        "created_at": str(resume.created_at) if resume.created_at else None,
    }
