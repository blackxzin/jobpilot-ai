"""Applications infrastructure — SQLAlchemy repository."""
from __future__ import annotations

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import ApplicationModel
from modules.applications.domain.entities import Application


class SQLAlchemyApplicationRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, application_id: str) -> Optional[ApplicationModel]:
        return await self._session.get(ApplicationModel, application_id)

    async def get_for_user(self, user_id: str) -> list[ApplicationModel]:
        result = await self._session.execute(
            select(ApplicationModel).where(ApplicationModel.user_id == user_id).order_by(ApplicationModel.created_at.desc())
        )
        return result.scalars().all()

    async def create(self, app: Application) -> ApplicationModel:
        model = ApplicationModel(
            id=str(app.id),
            job_id=str(app.job_id),
            resume_id=str(app.resume_id),
            user_id=str(app.user_id),
            status=app.status.value if hasattr(app.status, "value") else app.status,
            cover_letter=app.cover_letter,
            custom_message=app.custom_message,
            applied_at=app.applied_at,
            responded_at=app.responded_at,
            source_platform=app.source_platform,
            tracking_data=app.tracking_data,
            created_at=app.created_at,
            updated_at=app.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def update_status(self, application_id: str, status: str) -> Optional[ApplicationModel]:
        model = await self._session.get(ApplicationModel, application_id)
        if model:
            from datetime import datetime, UTC
            model.status = status
            model.updated_at = datetime.now(UTC)
            await self._session.flush()
        return model

    async def delete(self, application_id: str) -> None:
        model = await self._session.get(ApplicationModel, application_id)
        if model:
            await self._session.delete(model)
