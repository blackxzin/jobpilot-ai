"""Jobs infrastructure — SQLAlchemy repository."""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.models import CompanyModel, JobModel


class JobRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, job_id: str) -> JobModel | None:
        stmt = select(JobModel).options(selectinload(JobModel.company)).where(JobModel.id == job_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(self, query: str = "", location: str = "", remote: bool = False, page: int = 1, per_page: int = 20):
        stmt = select(JobModel).options(selectinload(JobModel.company)).where(JobModel.is_active.is_(True))
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
            stmt = stmt.where(JobModel.is_remote.is_(True))
        stmt = stmt.offset((page - 1) * per_page).limit(per_page).order_by(JobModel.created_at.desc())
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def create(self, data: dict) -> JobModel:
        model = JobModel(**data)
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_or_create_company(self, name: str) -> CompanyModel:
        stmt = select(CompanyModel).where(func.lower(CompanyModel.name) == name.strip().lower())
        result = await self._session.execute(stmt)
        company = result.scalar_one_or_none()
        if company:
            return company
        company = CompanyModel(name=name.strip())
        self._session.add(company)
        await self._session.flush()
        return company
