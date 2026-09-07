"""Resume infrastructure — SQLAlchemy repository."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import ResumeModel


class ResumeRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, resume_id: str) -> ResumeModel | None:
        return await self._session.get(ResumeModel, resume_id)

    async def get_latest_for_user(self, user_id: str) -> ResumeModel | None:
        """Return the user's most recently uploaded resume, if any."""
        result = await self._session.execute(
            select(ResumeModel)
            .where(ResumeModel.user_id == user_id)
            .order_by(ResumeModel.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str) -> list[ResumeModel]:
        result = await self._session.execute(
            select(ResumeModel).where(ResumeModel.user_id == user_id).order_by(ResumeModel.created_at.desc())
        )
        return result.scalars().all()

    async def create(self, user_id: str, title: str, content_text: str, file_url: str) -> ResumeModel:
        """Persist a resume and return the row.

        Returns the model rather than a dict so the route serializes uploads
        the same way it serializes list and get — the three used to disagree
        on field names.
        """
        model = ResumeModel(
            user_id=user_id,
            title=title,
            content_text=content_text,
            file_url=file_url,
        )
        self._session.add(model)
        await self._session.flush()
        return model
