"""AI analysis routes — LinkedIn & GitHub import."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.logger import get_logger
from core.models import LLMProviderConfigModel
from core.security import decrypt_api_key
from modules.auth.infrastructure.repositories import SQLAlchemyUserRepository, SQLAlchemySessionRepository
from modules.auth.application.use_cases import GetCurrentUserUseCase
from modules.ai.infrastructure.providers.factory import LLMProviderFactory
from modules.ai.application.llm_service import LLMService
from modules.resume.infrastructure.repositories import ResumeRepository
from core.exceptions import NotFoundError

logger = get_logger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])


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


async def _get_provider(user_id: str, db: AsyncSession):
    result = await db.execute(
        select(LLMProviderConfigModel).where(
            LLMProviderConfigModel.user_id == user_id,
            LLMProviderConfigModel.is_active == True,
        )
    )
    configs = result.scalars().all()
    config = configs[0] if configs else None
    if config:
        api_key = decrypt_api_key(config.api_key_encrypted) if config.api_key_encrypted else ""
        return LLMProviderFactory.create(config.provider_name, api_key=api_key, model=config.model)
    return LLMProviderFactory.create("openai")


@router.post("/linkedin/analyze")
async def analyze_linkedin(body: LinkedInRequest, authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    user = await auth_uc.execute(token)

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
    try:
        import json, re
        match = re.search(r'\{.*\}', result, re.DOTALL)
        return json.loads(match.group()) if match else {"raw": result}
    except:
        return {"analysis": result}


@router.post("/github/import")
async def import_github(body: GitHubRequest, authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
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
        return {"error": str(e)}
    finally:
        await client.close()


@router.post("/chat")
async def chat_ai(body: ChatRequest, authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    user = await auth_uc.execute(token)

    provider = await _get_provider(str(user.id), db)
    llm = LLMService(provider)

    prompt = f"""You are a career coach assistant for JobPilot AI. Be practical, direct, and helpful. Answer in Portuguese.

User: {body.message}"""
    response = await llm.generate(prompt)
    return {"response": response}


class AnalysisRequest(BaseModel):
    job_id: str
    resume_id: str


class TailorResumeRequest(BaseModel):
    resume_id: str
    job_id: str


@router.post("/match")
async def match_job(body: AnalysisRequest, authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    user = await auth_uc.execute(token)

    resume_repo = ResumeRepository(db)
    resume = await resume_repo.get_by_id(body.resume_id)
    if not resume:
        raise NotFoundError("Resume not found")

    from core.models import JobModel
    job_result = await db.execute(select(JobModel).where(JobModel.id == body.job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise NotFoundError("Job not found")

    provider = await _get_provider(str(user.id), db)
    llm = LLMService(provider)
    result = await llm.compare_job(
        resume.content_text,
        {"title": job.title, "company": job.company.name if job.company else "", "description": job.description, "skills": [], "requirements": []}
    )
    return result


@router.post("/ats-score")
async def ats_score(body: AnalysisRequest, authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    user = await auth_uc.execute(token)

    resume_repo = ResumeRepository(db)
    resume = await resume_repo.get_by_id(body.resume_id)
    if not resume:
        raise NotFoundError("Resume not found")

    from core.models import JobModel
    job_result = await db.execute(select(JobModel).where(JobModel.id == body.job_id))
    job = job_result.scalar_one_or_none()

    provider = await _get_provider(str(user.id), db)
    llm = LLMService(provider)
    result = await llm.analyze_resume(resume.content_text, job.description if job else "")
    return result


@router.post("/cover-letter")
async def cover_letter(body: AnalysisRequest, authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    user = await auth_uc.execute(token)

    resume_repo = ResumeRepository(db)
    resume = await resume_repo.get_by_id(body.resume_id)
    if not resume:
        raise NotFoundError("Resume not found")

    from core.models import JobModel
    job_result = await db.execute(select(JobModel).where(JobModel.id == body.job_id))
    job = job_result.scalar_one_or_none()

    provider = await _get_provider(str(user.id), db)
    llm = LLMService(provider)
    result = await llm.generate_cover_letter(
        resume.content_text,
        {"title": job.title if job else "", "company": job.company.name if job and job.company else "", "description": job.description if job else "", "requirements": []}
    )
    return {"cover_letter": result}


@router.post("/tailor-resume")
async def tailor_resume(body: TailorResumeRequest, authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    user = await auth_uc.execute(token)

    resume_repo = ResumeRepository(db)
    resume = await resume_repo.get_by_id(body.resume_id)
    if not resume:
        raise NotFoundError("Resume not found")

    from core.models import JobModel
    job_result = await db.execute(select(JobModel).where(JobModel.id == body.job_id))
    job = job_result.scalar_one_or_none()

    provider = await _get_provider(str(user.id), db)
    llm = LLMService(provider)
    tailored = await llm.generate_tailored_resume(
        resume.content_text,
        {"title": job.title if job else "", "company": job.company.name if job and job.company else "", "description": job.description if job else ""}
    )
    return {"tailored_resume": tailored}


class AutoApplyRequest(BaseModel):
    resume_id: str
    job_id: str


@router.post("/auto-apply")
async def auto_apply(body: AutoApplyRequest, authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    """Auto-apply: generate tailored resume + cover letter + create application."""
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    user = await auth_uc.execute(token)

    resume_repo = ResumeRepository(db)
    resume = await resume_repo.get_by_id(body.resume_id)
    if not resume:
        raise NotFoundError("Resume not found")

    from core.models import JobModel
    job_result = await db.execute(select(JobModel).where(JobModel.id == body.job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise NotFoundError("Job not found")

    provider = await _get_provider(str(user.id), db)
    llm = LLMService(provider)

    job_dict = {"title": job.title, "company": job.company.name if job.company else "", "description": job.description}

    tailored = await llm.generate_tailored_resume(resume.content_text, job_dict)
    cover = await llm.generate_cover_letter(resume.content_text, job_dict)

    from modules.applications.application.use_cases import CreateApplicationUseCase
    from modules.applications.infrastructure.repositories import SQLAlchemyApplicationRepository
    from modules.applications.application.use_cases import CreateApplicationDTO
    from uuid import UUID

    app_repo = SQLAlchemyApplicationRepository(db)
    app_uc = CreateApplicationUseCase(app_repo)
    dto = CreateApplicationDTO(
        job_id=UUID(body.job_id),
        resume_id=UUID(body.resume_id),
        user_id=user.id,
        cover_letter=cover,
        custom_message="Auto-applied via JobPilot AI",
        source_platform="auto_apply",
    )
    application = await app_uc.execute(dto)

    try:
        from workers.auto_apply import auto_apply as auto_apply_task
        auto_apply_task.delay(str(user.id), body.job_id, body.resume_id)
    except Exception:
        pass

    return {
        "application_id": str(application.id),
        "tailored_resume": tailored,
        "cover_letter": cover,
        "status": "applied",
    }
