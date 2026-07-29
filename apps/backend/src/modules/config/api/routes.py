"""LLM Provider Config API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import encrypt_api_key
from modules.auth.infrastructure.repositories import SQLAlchemyUserRepository, SQLAlchemySessionRepository
from modules.auth.application.use_cases import GetCurrentUserUseCase
from core.models import LLMProviderConfigModel
from sqlalchemy import select

router = APIRouter(prefix="/settings", tags=["settings"])

PROVIDERS = [
    {"id": "openai", "name": "OpenAI", "models": "gpt-4o, gpt-4o-mini, gpt-4", "needs_key": True, "needs_url": False},
    {"id": "anthropic", "name": "Anthropic Claude", "models": "claude-sonnet-4-20250514, claude-haiku-3-5", "needs_key": True, "needs_url": False},
    {"id": "gemini", "name": "Google Gemini", "models": "gemini-2.0-flash, gemini-2.0-pro", "needs_key": True, "needs_url": False},
    {"id": "ollama", "name": "Ollama (local)", "models": "llama3.1, mistral, qwen2", "needs_key": False, "needs_url": True},
    {"id": "nvidia_nim", "name": "NVIDIA NIM", "models": "nvidia/llama-3.3-70b-instruct", "needs_key": True, "needs_url": True},
    {"id": "openrouter", "name": "OpenRouter", "models": "openai/gpt-4o, meta-llama/llama-3.1", "needs_key": True, "needs_url": False},
]


class ProviderConfigRequest(BaseModel):
    provider_name: str
    api_key: str = ""
    base_url: str = ""
    model: str = ""


@router.get("/providers")
async def list_providers():
    return {"providers": PROVIDERS}


@router.get("/llm")
async def get_configs(authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    user = await auth_uc.execute(token)

    result = await db.execute(
        select(LLMProviderConfigModel).where(LLMProviderConfigModel.user_id == str(user.id))
    )
    configs = result.scalars().all()
    return {
        "configs": [
            {
                "id": c.id,
                "provider_name": c.provider_name,
                "has_key": bool(c.api_key_encrypted),
                "base_url": c.base_url,
                "model": c.model,
                "is_active": c.is_active,
            }
            for c in configs
        ]
    }


@router.post("/llm")
async def save_config(body: ProviderConfigRequest, authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    user = await auth_uc.execute(token)

    # Check if already exists
    result = await db.execute(
        select(LLMProviderConfigModel).where(
            LLMProviderConfigModel.user_id == str(user.id),
            LLMProviderConfigModel.provider_name == body.provider_name,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        if body.api_key:
            existing.api_key_encrypted = encrypt_api_key(body.api_key)
        if body.base_url:
            existing.base_url = body.base_url
        if body.model:
            existing.model = body.model
        existing.is_active = True
    else:
        import uuid
        config = LLMProviderConfigModel(
            id=str(uuid.uuid4()),
            user_id=str(user.id),
            provider_name=body.provider_name,
            api_key_encrypted=encrypt_api_key(body.api_key) if body.api_key else "",
            base_url=body.base_url,
            model=body.model or "",
            is_active=True,
        )
        db.add(config)

    await db.commit()
    return {"message": f"{body.provider_name} configurado com sucesso!"}
