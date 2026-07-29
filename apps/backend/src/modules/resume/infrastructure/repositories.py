"""Resume infrastructure — SQLAlchemy repository."""
from __future__ import annotations

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import ResumeModel


class ResumeRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, resume_id: str) -> Optional[ResumeModel]:
        return await self._session.get(ResumeModel, resume_id)

    async def list_by_user(self, user_id: str) -> list[ResumeModel]:
        result = await self._session.execute(
            select(ResumeModel).where(ResumeModel.user_id == user_id).order_by(ResumeModel.created_at.desc())
        )
        return result.scalars().all()

    async def create(self, user_id: str, title: str, content_text: str, file_url: str) -> dict:
        import uuid
        from datetime import datetime, UTC
        model = ResumeModel(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            content_text=content_text,
            file_url=file_url,
        )
        self._session.add(model)
        await self._session.flush()
        return {
            "id": model.id,
            "user_id": model.user_id,
            "title": model.title,
            "content_text": model.content_text[:200],
            "file_url": model.file_url,
            "created_at": str(model.created_at),
        }
