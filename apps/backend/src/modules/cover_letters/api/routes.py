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
    )
