"""Jobs infrastructure — SQLAlchemy repository."""
from __future__ import annotations

from typing import Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import JobModel, CompanyModel


class JobRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, job_id: str) -> Optional[JobModel]:
        return await self._session.get(JobModel, job_id)

    async def search(self, query: str = "", location: str = "", remote: bool = False, page: int = 1, per_page: int = 20):
        stmt = select(JobModel).where(JobModel.is_active == True)
        if query:
            stmt = stmt.where(
                or_(
                    JobModel.title.ilike(f"%{query}%"),
                    JobModel.description.ilike(f"%{query}%"),
                )
            )
        if location:
            stmt = stmt.where(JobModel.location.ilike(f"%{location}%"))
        if remote:
            stmt = stmt.where(JobModel.is_remote == True)
        stmt = stmt.offset((page - 1) * per_page).limit(per_page).order_by(JobModel.created_at.desc())
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def create(self, data: dict) -> JobModel:
        model = JobModel(**data)
        self._session.add(model)
        await self._session.flush()
        return model
