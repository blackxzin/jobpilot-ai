"""Cover letters infrastructure — SQLAlchemy repo."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from core.models import CoverLetterModel


class CoverLetterRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, user_id: str, job_id: str, content: str) -> dict:
        import uuid
        model = CoverLetterModel(
            id=str(uuid.uuid4()),
            user_id=user_id,
            job_id=job_id,
            content=content,
        )
        self._session.add(model)
        await self._session.flush()
        return {"id": model.id, "user_id": model.user_id, "content": content, "created_at": str(model.created_at)}
