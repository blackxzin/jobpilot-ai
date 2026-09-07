"""AI analysis routes — matching, ATS, cover letter, chat, LinkedIn & GitHub import."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.config import settings
from core.database import get_db
from core.exceptions import JobPilotException, NotFoundError, ValidationError
from core.logger import get_logger
from core.models import JobModel, LLMProviderConfigModel
from core.security import decrypt_api_key
from core.validators import validate_uuid
from modules.ai.application.llm_service import LLMService
from modules.ai.infrastructure.providers.factory import LLMProviderFactory
from modules.auth.api.dependencies import ensure_owner, get_current_user
from modules.auth.domain.entities import User
from modules.resume.infrastructure.repositories import ResumeRepository

logger = get_logger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])


# ── Request models ──────────────────────────────────────────────────────────

class ProfileSuggestionRequest(BaseModel):
    """Input for profile positioning.

    `resume_id` is optional: without it the user's most recent resume is used,
    which is what the UI sends.
    """

    resume_id: str = ""
    target_role: str = ""
    url: str = ""


class GitHubRequest(BaseModel):
    username: str


class ChatRequest(BaseModel):
    message: str
    context: str = ""


class AnalysisRequest(BaseModel):
    job_id: str
    resume_id: str


class CoverLetterRequest(AnalysisRequest):
    language: str = "pt-BR"
    tone: str = "professional"


class TailorResumeRequest(BaseModel):
    resume_id: str
    job_id: str


class AutoApplyRequest(BaseModel):
    resume_id: str
    job_id: str


# ── Helpers ─────────────────────────────────────────────────────────────────

async def _get_provider(user_id: str, db: AsyncSession):
    """Return the LLM provider configured by the user, or a working default.

    Resolution order: the user's own active configuration, then the app-wide
    NVIDIA NIM key, then the offline analyzer. The last step matters — without
    it a fresh install answers every AI request with a 502.
    """
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
        return LLMProviderFactory.create_with_fallback(
            config.provider_name,
            api_key=api_key,
            base_url=config.base_url or "",
            model=config.model or "",
        )
    # OPENAI_API_KEY holds an OpenAI-compatible NVIDIA NIM key when set.
    return LLMProviderFactory.create_with_fallback(
        "nvidia_nim", api_key=settings.OPENAI_API_KEY
    )


async def _load_job(db: AsyncSession, job_id: str) -> JobModel:
    """Load a job by id, or raise NotFoundError.

    Relationships are eager-loaded: touching a lazy relationship inside async
    SQLAlchemy raises MissingGreenlet. The id is validated first so a
    malformed UUID is a 422 rather than a driver-level 500.
    """
    result = await db.execute(
        select(JobModel)
        .options(selectinload(JobModel.company), selectinload(JobModel.requirements))
        .where(JobModel.id == validate_uuid(job_id, "job_id"))
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise NotFoundError("Job not found")
    return job


async def _load_owned_resume(db: AsyncSession, resume_id: str, user: User):
    """Load a resume and verify it belongs to the current user."""
    resume = await ResumeRepository(db).get_by_id(validate_uuid(resume_id, "resume_id"))
    if not resume:
        raise NotFoundError("Resume not found")
    ensure_owner(resume.user_id, user, "Resume")
    return resume


def _job_to_prompt_dict(job: JobModel) -> dict:
    """Build the plain dict the LLM providers expect from a job."""
    requirements = [r.requirement for r in (job.requirements or []) if r.category != "skill"]
    skills = [r.requirement for r in (job.requirements or []) if r.category == "skill"]
    return {
        "title": job.title or "",
        "company": job.company.name if job.company else "",
        "description": job.description or "",
        "requirements": requirements,
        "skills": skills,
    }


# ── Routes ──────────────────────────────────────────────────────────────────

@router.post("/linkedin/analyze")
async def suggest_profile(
    body: ProfileSuggestionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Suggest how to present the user's experience on a professional profile.

    This used to ask the model to infer a person's profile from a LinkedIn URL
    alone, which produced a confident, wholly invented biography — the model
    has no access to the page. It now works from the user's own uploaded
    resume, so every suggestion is traceable to something they wrote.
    """
    if body.resume_id:
        resume = await _load_owned_resume(db, body.resume_id, user)
    else:
        resume = await ResumeRepository(db).get_latest_for_user(str(user.id))
        if resume is None:
            raise ValidationError(
                "Envie um currículo primeiro — as sugestões de perfil são geradas a "
                "partir dele, não do endereço do LinkedIn."
            )

    llm = LLMService(await _get_provider(str(user.id), db))
    result = await llm.suggest_profile(resume.content_text or "", body.target_role)

    if "parse_error" in result:
        # The model answered in prose. Surfacing it beats an empty shape.
        return {"analysis": result.get("raw", ""), "url": body.url}
    return {**result, "url": body.url}


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
    except JobPilotException:
        raise
    except Exception as e:
        # Surfacing the raw client exception would leak internals; the log keeps it.
        logger.warning("github_import_failed", username=body.username, error=str(e))
        raise NotFoundError(
            f"Não foi possível importar o perfil '{body.username}' do GitHub. "
            "Verifique se o usuário existe e é público."
        ) from e
    finally:
        await client.close()


@router.post("/chat")
async def chat_ai(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    llm = LLMService(await _get_provider(str(user.id), db))
    response = await llm.answer_question(body.message, body.context)
    return {"response": response, "provider": llm.provider_name}


@router.post("/match")
async def match_job(
    body: AnalysisRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resume = await _load_owned_resume(db, body.resume_id, user)
    job = await _load_job(db, body.job_id)

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
    return await llm.analyze_resume(resume.content_text or "", job.description or "")


@router.post("/cover-letter")
async def cover_letter(
    body: CoverLetterRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a cover letter and persist it so it shows up in cover-letter history."""
    from modules.cover_letters.application.use_cases import GenerateCoverLetterUseCase
    from modules.cover_letters.infrastructure.repositories import CoverLetterRepository

    resume = await _load_owned_resume(db, body.resume_id, user)
    job = await _load_job(db, body.job_id)

    llm = LLMService(await _get_provider(str(user.id), db))
    use_case = GenerateCoverLetterUseCase(llm, CoverLetterRepository(db))
    saved = await use_case.execute(
        user_id=str(user.id),
        job_id=body.job_id,
        resume_text=resume.content_text or "",
        job=_job_to_prompt_dict(job),
        language=body.language,
        tone=body.tone,
    )
    return {"cover_letter": saved["content"], "id": saved["id"]}


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

    # No background dispatch here: this route already generated both documents
    # and persisted the application. Queueing `workers.auto_apply` as well
    # would redo the same work for a job that is already applied to.
    return {
        "application_id": str(application.id),
        "tailored_resume": tailored,
        "cover_letter": cover,
        "status": "applied",
    }
