"""AI analysis routes — matching, ATS, cover letter, chat, LinkedIn & GitHub import."""
from __future__ import annotations

import json
import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.config import settings
from core.database import get_db
from core.exceptions import NotFoundError
from core.logger import get_logger
from core.models import JobModel, LLMProviderConfigModel
from core.security import decrypt_api_key
from modules.ai.application.llm_service import LLMService
from modules.ai.infrastructure.providers.factory import LLMProviderFactory
from modules.auth.api.dependencies import ensure_owner, get_current_user
from modules.auth.domain.entities import User
from modules.resume.infrastructure.repositories import ResumeRepository

logger = get_logger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])


# ── Request models ──────────────────────────────────────────────────────────

class LinkedInRequest(BaseModel):
    url: str


class GitHubRequest(BaseModel):
    username: str


class ChatRequest(BaseModel):
    message: str
    context: str = ""


class AnalysisRequest(BaseModel):
    job_id: str
    resume_id: str


class TailorResumeRequest(BaseModel):
    resume_id: str
    job_id: str


class AutoApplyRequest(BaseModel):
    resume_id: str
    job_id: str


# ── Helpers ─────────────────────────────────────────────────────────────────

async def _get_provider(user_id: str, db: AsyncSession):
    """Return the LLM provider configured by the user, or the app default."""
    result = await db.execute(
        select(LLMProviderConfigModel)
        .where(
            LLMProviderConfigModel.user_id == user_id,
            LLMProviderConfigModel.is_active.is_(True),
        )
        .order_by(LLMProviderConfigModel.created_at.desc())
    )
    config = result.scalars().first()
    if config:
        api_key = decrypt_api_key(config.api_key_encrypted) if config.api_key_encrypted else ""
        return LLMProviderFactory.create(
            config.provider_name,
            api_key=api_key,
            base_url=config.base_url or "",
            model=config.model or "",
        )
    # Fallback: OPENAI_API_KEY holds an OpenAI-compatible NVIDIA NIM key.
    return LLMProviderFactory.create("nvidia_nim", api_key=settings.OPENAI_API_KEY)


async def _load_job(db: AsyncSession, job_id: str) -> JobModel | None:
    """Load a job with its company eagerly loaded.

    The company relationship must be eager-loaded: touching a lazy relationship
    inside async SQLAlchemy raises MissingGreenlet.
    """
    result = await db.execute(
        select(JobModel).options(selectinload(JobModel.company)).where(JobModel.id == job_id)
    )
    return result.scalar_one_or_none()


async def _load_owned_resume(db: AsyncSession, resume_id: str, user: User):
    """Load a resume and verify it belongs to the current user."""
    resume = await ResumeRepository(db).get_by_id(resume_id)
    if not resume:
        raise NotFoundError("Resume not found")
    ensure_owner(resume.user_id, user, "Resume")
    return resume


def _job_to_prompt_dict(job: JobModel | None) -> dict:
    """Build the plain dict the LLM providers expect from a job."""
    if job is None:
        return {"title": "", "company": "", "description": "", "requirements": [], "skills": []}
    return {
        "title": job.title or "",
        "company": job.company.name if job.company else "",
        "description": job.description or "",
        "requirements": [],
        "skills": [],
    }


def _extract_json(text: str) -> dict | None:
    """Best-effort extraction of a JSON object from an LLM response."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


# ── Routes ──────────────────────────────────────────────────────────────────

@router.post("/linkedin/analyze")
async def analyze_linkedin(
    body: LinkedInRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    provider = await _get_provider(str(user.id), db)
    llm = LLMService(provider)

    prompt = f"""You are a career analyst. Based on this LinkedIn URL, infer the most likely profile information.

LinkedIn URL: {body.url}

Return a JSON with these keys:
- "name": inferred full name
- "headline": likely headline/title
- "skills": array of likely technical and professional skills
- "experience_years": estimated years of experience
- "suggested_roles": array of job roles this person would be a good fit for
- "analysis": brief career analysis in Portuguese

Return ONLY valid JSON."""
    result = await llm.generate(prompt)
    parsed = _extract_json(result)
    return parsed if parsed is not None else {"analysis": result}


@router.post("/github/import")
async def import_github(
    body: GitHubRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from modules.users.infrastructure.providers.github_client import GitHubClient

    client = GitHubClient()
    try:
        user_data = await client.get_user(body.username)
        repos = await client.get_repositories(body.username)
        skills = await client.get_skills(body.username)
        return {
            "profile": user_data,
            "repos": repos[:10],
            "skills": skills,
            "total_repos": len(repos),
        }
    except Exception as e:
        logger.warning("github_import_failed", username=body.username, error=str(e))
        return {"error": str(e)}
    finally:
        await client.close()


@router.post("/chat")
async def chat_ai(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    provider = await _get_provider(str(user.id), db)
    llm = LLMService(provider)

    prompt = f"""You are a career coach assistant for JobPilot AI. Be practical, direct, and helpful. Answer in Portuguese.

User: {body.message}"""
    response = await llm.generate(prompt)
    return {"response": response}


@router.post("/match")
async def match_job(
    body: AnalysisRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resume = await _load_owned_resume(db, body.resume_id, user)
    job = await _load_job(db, body.job_id)
    if not job:
        raise NotFoundError("Job not found")

    llm = LLMService(await _get_provider(str(user.id), db))
    return await llm.compare_job(resume.content_text, _job_to_prompt_dict(job))


@router.post("/ats-score")
async def ats_score(
    body: AnalysisRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resume = await _load_owned_resume(db, body.resume_id, user)
    job = await _load_job(db, body.job_id)

    llm = LLMService(await _get_provider(str(user.id), db))
    return await llm.analyze_resume(resume.content_text, job.description if job else "")


@router.post("/cover-letter")
async def cover_letter(
    body: AnalysisRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resume = await _load_owned_resume(db, body.resume_id, user)
    job = await _load_job(db, body.job_id)

    llm = LLMService(await _get_provider(str(user.id), db))
    result = await llm.generate_cover_letter(resume.content_text, _job_to_prompt_dict(job))
    return {"cover_letter": result}


@router.post("/tailor-resume")
async def tailor_resume(
    body: TailorResumeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resume = await _load_owned_resume(db, body.resume_id, user)
    job = await _load_job(db, body.job_id)

    llm = LLMService(await _get_provider(str(user.id), db))
    tailored = await llm.generate_tailored_resume(resume.content_text, _job_to_prompt_dict(job))
    return {"tailored_resume": tailored}


@router.post("/auto-apply")
async def auto_apply(
    body: AutoApplyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Auto-apply: generate tailored resume + cover letter + create application."""
    from uuid import UUID

    from modules.applications.application.use_cases import (
        CreateApplicationDTO,
        CreateApplicationUseCase,
    )
    from modules.applications.infrastructure.repositories import SQLAlchemyApplicationRepository

    resume = await _load_owned_resume(db, body.resume_id, user)
    job = await _load_job(db, body.job_id)
    if not job:
        raise NotFoundError("Job not found")

    llm = LLMService(await _get_provider(str(user.id), db))
    job_dict = _job_to_prompt_dict(job)

    tailored = await llm.generate_tailored_resume(resume.content_text, job_dict)
    cover = await llm.generate_cover_letter(resume.content_text, job_dict)

    app_use_case = CreateApplicationUseCase(SQLAlchemyApplicationRepository(db))
    application = await app_use_case.execute(
        CreateApplicationDTO(
            job_id=UUID(str(job.id)),
            resume_id=UUID(str(resume.id)),
            user_id=user.id,
            cover_letter=cover,
            custom_message="Auto-applied via JobPilot AI",
            source_platform="auto_apply",
        )
    )

    try:
        from workers.auto_apply import auto_apply as auto_apply_task

        auto_apply_task.delay(str(user.id), body.job_id, body.resume_id)
    except Exception as e:
        # The application row is already persisted; the async task is best-effort.
        logger.warning("auto_apply_task_dispatch_failed", error=str(e))

    return {
        "application_id": str(application.id),
        "tailored_resume": tailored,
        "cover_letter": cover,
        "status": "applied",
    }
