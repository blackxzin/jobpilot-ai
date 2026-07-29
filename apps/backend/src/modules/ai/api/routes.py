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

logger = get_logger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])


class LinkedInRequest(BaseModel):
    url: str


class GitHubRequest(BaseModel):
    username: str


class ChatRequest(BaseModel):
    message: str
    context: str = ""


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
