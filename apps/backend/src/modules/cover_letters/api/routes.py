"""Cover letters API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from modules.auth.infrastructure.repositories import SQLAlchemyUserRepository, SQLAlchemySessionRepository
from modules.auth.application.use_cases import GetCurrentUserUseCase
from modules.cover_letters.application.use_cases import GenerateCoverLetterUseCase
from modules.cover_letters.infrastructure.repositories import CoverLetterRepository
from modules.resume.infrastructure.repositories import ResumeRepository
from modules.jobs.infrastructure.repositories import JobRepository
from modules.ai.infrastructure.providers.factory import LLMProviderFactory
from modules.ai.application.llm_service import LLMService

router = APIRouter(prefix="/cover-letters", tags=["cover-letters"])


class GenerateRequest(BaseModel):
    job_id: str
    resume_id: str


@router.post("/generate")
async def generate(body: GenerateRequest, authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    user = await auth_uc.execute(token)

    resume_repo = ResumeRepository(db)
    resume = await resume_repo.get_by_id(body.resume_id)

    job_repo = JobRepository(db)
    job = await job_repo.get_by_id(body.job_id)

    provider = LLMProviderFactory.create("openai")
    llm_service = LLMService(provider)
    repo = CoverLetterRepository(db)
    use_case = GenerateCoverLetterUseCase(llm_service, repo)

    resume_text = resume.content_text if hasattr(resume, "content_text") else ""
    job_data = {
        "title": job.title,
        "company": getattr(job, "company_name", "") or "",
        "description": job.description,
        "requirements": [],
        "skills": [],
    }
    result = await use_case.execute(user_id=str(user.id), job_id=body.job_id, resume_text=resume_text, job=job_data)
    return result
