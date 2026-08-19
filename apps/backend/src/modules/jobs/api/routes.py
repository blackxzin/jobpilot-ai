"""Jobs API routes — local + multi-source."""
from __future__ import annotations

from asyncio import gather

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.logger import get_logger
from modules.jobs.application.use_cases import GetJobUseCase, SearchJobsUseCase
from modules.jobs.infrastructure.repositories import JobRepository
from modules.users.infrastructure.providers.google_jobs_client import GoogleJobsClient
from modules.users.infrastructure.providers.indeed_client import IndeedClient
from modules.users.infrastructure.providers.jobicy_client import JobicyClient
from modules.users.infrastructure.providers.linkedin_jobs_client import LinkedInJobsClient
from modules.users.infrastructure.providers.remoteok_client import RemoteOKClient

logger = get_logger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])

async def _search_external(source: str, client, **kwargs) -> dict:
    """Run one external job-board search, never propagating provider failures.

    An unreachable job board must not fail the whole request, so the source
    returns an empty result set instead. The client is always closed.
    """
    try:
        jobs = await client.search_jobs(**kwargs)
        return {"results": jobs if isinstance(jobs, list) else [], "source": source}
    except Exception as e:
        logger.warning("job_source_search_failed", source=source, error=str(e))
        return {"results": [], "source": source}
    finally:
        await client.close()


@router.get("")
async def search_jobs(
    q: str = Query("", alias="query"),
    location: str = "",
    remote: bool = False,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    use_case = SearchJobsUseCase(JobRepository(db))
    results = await use_case.execute(
        query=q, location=location, remote=remote, page=page, per_page=per_page
    )
    return {"results": [_to_dict(j) for j in results], "page": page, "per_page": per_page}


@router.get("/remoteok")
async def search_remoteok(q: str = Query(""), page: int = Query(1, ge=1)):
    return await _search_external("remoteok", RemoteOKClient(), query=q, page=page)


@router.get("/jobicy")
async def search_jobicy(q: str = Query(""), page: int = Query(1, ge=1)):
    return await _search_external("jobicy", JobicyClient(), query=q, page=page)


@router.get("/google-jobs")
async def search_google_jobs(q: str = Query(""), location: str = "", page: int = Query(1, ge=1)):
    return await _search_external(
        "google_jobs", GoogleJobsClient(), query=q, location=location, page=page
    )


@router.get("/gupy")
async def search_gupy(
    q: str = Query(""), location: str = "", remote: bool = False, page: int = Query(1, ge=1)
):
    from modules.jobs.application.use_cases import SearchGupyUseCase

    try:
        return await SearchGupyUseCase().execute(
            query=q, location=location, remote=remote, page=page
        )
    except Exception as e:
        logger.warning("job_source_search_failed", source="gupy", error=str(e))
        return {"results": [], "source": "gupy"}


@router.get("/indeed")
async def search_indeed(q: str = Query(""), location: str = "", page: int = Query(1, ge=1)):
    return await _search_external(
        "indeed", IndeedClient(), query=q, location=location, page=page
    )


@router.get("/linkedin")
async def search_linkedin_jobs(q: str = Query(""), location: str = "", page: int = Query(1, ge=1)):
    return await _search_external(
        "linkedin", LinkedInJobsClient(), query=q, location=location, page=page
    )


@router.get("/geekhunter")
async def search_geekhunter(q: str = Query(""), page: int = Query(1, ge=1)):
    from modules.users.infrastructure.providers.geekhunter_client import GeekHunterClient

    return await _search_external("geekhunter", GeekHunterClient(), query=q, page=page)


@router.get("/programathor")
async def search_programathor(q: str = Query(""), page: int = Query(1, ge=1)):
    from modules.users.infrastructure.providers.programathor_client import ProgramathorClient

    return await _search_external("programathor", ProgramathorClient(), query=q, page=page)


@router.get("/search-all")
async def search_all(q: str = Query(""), page: int = Query(1, ge=1)):
    """Query every remote-friendly source in parallel and merge the results."""
    sources = [
        _search_external("remoteok", RemoteOKClient(), query=q, page=page),
        _search_external("jobicy", JobicyClient(), query=q, page=page),
        _search_external("google_jobs", GoogleJobsClient(), query=q, page=page),
    ]
    outcomes = await gather(*sources, return_exceptions=True)

    merged = []
    for outcome in outcomes:
        if isinstance(outcome, dict) and outcome.get("results"):
            merged.append({"source": outcome["source"], "jobs": outcome["results"]})
    return {"results": merged}


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
