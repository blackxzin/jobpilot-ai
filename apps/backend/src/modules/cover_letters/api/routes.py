"""Cover letters API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.exceptions import NotFoundError
from modules.ai.api.routes import _get_provider, _job_to_prompt_dict, _load_job
from modules.ai.application.llm_service import LLMService
from modules.auth.api.dependencies import ensure_owner, get_current_user
from modules.auth.domain.entities import User
from modules.cover_letters.application.use_cases import GenerateCoverLetterUseCase
from modules.cover_letters.infrastructure.repositories import CoverLetterRepository
from modules.resume.infrastructure.repositories import ResumeRepository

router = APIRouter(prefix="/cover-letters", tags=["cover-letters"])


class GenerateRequest(BaseModel):
    job_id: str
    resume_id: str
    language: str = "pt-BR"
    tone: str = "professional"


class UpdateRequest(BaseModel):
    content: str
    title: str | None = None


async def _load_owned_cover_letter(db: AsyncSession, cover_letter_id: str, user: User):
    model = await CoverLetterRepository(db).get_by_id(cover_letter_id)
    if not model:
        raise NotFoundError("Cover letter not found")
    ensure_owner(model.user_id, user, "Cover letter")
    return model


@router.post("/generate")
async def generate(
    body: GenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resume = await ResumeRepository(db).get_by_id(body.resume_id)
    if not resume:
        raise NotFoundError("Resume not found")
    ensure_owner(resume.user_id, user, "Resume")

    job = await _load_job(db, body.job_id)
    if not job:
        raise NotFoundError("Job not found")

    llm_service = LLMService(await _get_provider(str(user.id), db))
    use_case = GenerateCoverLetterUseCase(llm_service, CoverLetterRepository(db))
    return await use_case.execute(
        user_id=str(user.id),
        job_id=body.job_id,
        resume_text=resume.content_text or "",
        job=_job_to_prompt_dict(job),
        language=body.language,
        tone=body.tone,
    )


@router.get("")
async def list_cover_letters(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's generated cover letters, most recent first."""
    return await CoverLetterRepository(db).list_by_user(str(user.id))


@router.get("/{cover_letter_id}")
async def get_cover_letter(
    cover_letter_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    model = await _load_owned_cover_letter(db, cover_letter_id, user)
    return {
        "id": model.id,
        "user_id": model.user_id,
        "job_id": model.job_id,
        "title": model.title,
        "content": model.content,
        "language": model.language,
        "tone": model.tone,
        "created_at": str(model.created_at),
        "updated_at": str(model.updated_at),
    }


@router.patch("/{cover_letter_id}")
async def update_cover_letter(
    cover_letter_id: str,
    body: UpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save manual edits made to a generated letter."""
    model = await _load_owned_cover_letter(db, cover_letter_id, user)
    return await CoverLetterRepository(db).update(model, content=body.content, title=body.title)


@router.delete("/{cover_letter_id}", status_code=204)
async def delete_cover_letter(
    cover_letter_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    model = await _load_owned_cover_letter(db, cover_letter_id, user)
    await CoverLetterRepository(db).delete(model)
