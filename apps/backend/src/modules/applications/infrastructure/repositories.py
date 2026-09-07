"""Applications infrastructure — SQLAlchemy repository."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import ApplicationModel, CompanyModel, JobModel
from modules.applications.domain.entities import Application


class SQLAlchemyApplicationRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, application_id: str) -> ApplicationModel | None:
        return await self._session.get(ApplicationModel, application_id)

    async def get_for_user(self, user_id: str) -> list[ApplicationModel]:
        result = await self._session.execute(
            select(ApplicationModel).where(ApplicationModel.user_id == user_id).order_by(ApplicationModel.created_at.desc())
        )
        return result.scalars().all()

    async def get_for_user_with_job(self, user_id: str) -> list[tuple[ApplicationModel, str, str]]:
        """Return each application alongside its job title and company name.

        The list endpoint could only echo raw UUIDs without this, so the
        pipeline showed rows reading "Job: a1b2c3d4…" instead of the role the
        user actually applied for. Outer joins keep applications visible even
        if the job or company row was removed.
        """
        result = await self._session.execute(
            select(
                ApplicationModel,
                JobModel.title,
                CompanyModel.name,
            )
            .outerjoin(JobModel, ApplicationModel.job_id == JobModel.id)
            .outerjoin(CompanyModel, JobModel.company_id == CompanyModel.id)
            .where(ApplicationModel.user_id == user_id)
            .order_by(ApplicationModel.created_at.desc())
        )
        return [(row[0], row[1] or "", row[2] or "") for row in result.all()]

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

    async def update_status(self, application_id: str, status: str) -> ApplicationModel | None:
        model = await self._session.get(ApplicationModel, application_id)
        if model:
            from datetime import UTC, datetime
            model.status = status
            model.updated_at = datetime.now(UTC)
            await self._session.flush()
        return model

    async def delete(self, application_id: str) -> None:
        model = await self._session.get(ApplicationModel, application_id)
        if model:
            await self._session.delete(model)
