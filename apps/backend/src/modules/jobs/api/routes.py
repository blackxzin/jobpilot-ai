"""Jobs API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from modules.jobs.application.use_cases import SearchJobsUseCase, GetJobUseCase, SearchGupyUseCase
from modules.jobs.infrastructure.repositories import JobRepository

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
async def search_jobs(
    q: str = Query("", alias="query"),
    location: str = "",
    remote: bool = False,
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
):
    use_case = SearchJobsUseCase(JobRepository(db))
    results = await use_case.execute(query=q, location=location, remote=remote, page=page, per_page=per_page)
    return {"results": [self._to_dict(j) for j in results], "page": page, "per_page": per_page}

@router.get("/gupy")
async def search_gupy(
    q: str = Query("", alias="query"),
    location: str = "",
    remote: bool = False,
    page: int = 1,
):
    use_case = SearchGupyUseCase()
    return await use_case.execute(query=q, location=location, remote=remote, page=page)

@router.get("/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    use_case = GetJobUseCase(JobRepository(db))
    job = await use_case.execute(job_id)
    return _to_dict(job)

def _to_dict(job):
    return {
        "id": job.id,
        "source": job.source,
        "title": job.title,
        "company_id": job.company_id,
        "description": job.description,
        "location": job.location,
        "location_type": job.location_type,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "currency": job.currency,
        "apply_url": job.apply_url,
        "is_remote": job.is_remote,
        "posted_at": str(job.posted_at) if job.posted_at else None,
        "created_at": str(job.created_at) if job.created_at else None,
    }
