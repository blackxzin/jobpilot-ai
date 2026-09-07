"""Cover letters infrastructure — SQLAlchemy repo."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import CoverLetterModel


def _to_dict(model: CoverLetterModel) -> dict:
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


class CoverLetterRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        user_id: str,
        job_id: str,
        content: str,
        title: str = "",
        language: str = "pt-BR",
        tone: str = "professional",
    ) -> dict:
        model = CoverLetterModel(
            id=str(uuid.uuid4()),
            user_id=user_id,
            job_id=job_id,
            title=title,
            content=content,
            language=language,
            tone=tone,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_dict(model)

    async def get_by_id(self, cover_letter_id: str) -> CoverLetterModel | None:
        result = await self._session.execute(
            select(CoverLetterModel).where(CoverLetterModel.id == cover_letter_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str, limit: int = 50) -> list[dict]:
        result = await self._session.execute(
            select(CoverLetterModel)
            .where(CoverLetterModel.user_id == user_id)
            .order_by(CoverLetterModel.created_at.desc())
            .limit(limit)
        )
        return [_to_dict(model) for model in result.scalars().all()]

    async def update(self, model: CoverLetterModel, content: str, title: str | None = None) -> dict:
        model.content = content
        if title is not None:
            model.title = title
        await self._session.flush()
        return _to_dict(model)

    async def delete(self, model: CoverLetterModel) -> None:
        await self._session.delete(model)
        await self._session.flush()
