"""Jobs API routes — local + multi-source."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.logger import get_logger
from modules.jobs.application.use_cases import SearchJobsUseCase, GetJobUseCase
from modules.jobs.infrastructure.repositories import JobRepository
from modules.users.infrastructure.providers.remoteok_client import RemoteOKClient
from modules.users.infrastructure.providers.jobicy_client import JobicyClient
from modules.users.infrastructure.providers.google_jobs_client import GoogleJobsClient
from modules.users.infrastructure.providers.indeed_client import IndeedClient
from modules.users.infrastructure.providers.linkedin_jobs_client import LinkedInJobsClient

logger = get_logger(__name__)

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
    return {"results": [_to_dict(j) for j in results], "page": page, "per_page": per_page}


@router.get("/remoteok")
async def search_remoteok(q: str = Query(""), page: int = 1):
    client = RemoteOKClient()
    try:
        jobs = await client.search_jobs(query=q, page=page)
        return {"results": jobs, "source": "remoteok"}
    except Exception as e:
        logger.warning("remoteok_search_failed", error=str(e))
        return {"results": [], "source": "remoteok"}
    finally:
        await client.close()


@router.get("/jobicy")
async def search_jobicy(q: str = Query(""), page: int = 1):
    client = JobicyClient()
    try:
        jobs = await client.search_jobs(query=q, page=page)
        return {"results": jobs, "source": "jobicy"}
    except Exception as e:
        logger.warning("jobicy_search_failed", error=str(e))
        return {"results": [], "source": "jobicy"}
    finally:
        await client.close()


@router.get("/google-jobs")
async def search_google_jobs(q: str = Query(""), location: str = "", page: int = 1):
    client = GoogleJobsClient()
    try:
        jobs = await client.search_jobs(query=q, location=location, page=page)
        return {"results": jobs, "source": "google_jobs"}
    except Exception as e:
        logger.warning("google_jobs_search_failed", error=str(e))
        return {"results": [], "source": "google_jobs"}
    finally:
        await client.close()


@router.get("/gupy")
async def search_gupy(q: str = Query(""), location: str = "", remote: bool = False, page: int = 1):
    try:
        from modules.jobs.application.use_cases import SearchGupyUseCase
        use_case = SearchGupyUseCase()
        return await use_case.execute(query=q, location=location, remote=remote, page=page)
    except Exception as e:
        logger.warning("gupy_search_failed", error=str(e))
        return {"results": [], "source": "gupy"}


@router.get("/indeed")
async def search_indeed(q: str = Query(""), location: str = "", page: int = 1):
    client = IndeedClient()
    try:
        jobs = await client.search_jobs(query=q, location=location, page=page)
        return {"results": jobs, "source": "indeed"}
    except Exception as e:
        logger.warning("indeed_search_failed", error=str(e))
        return {"results": [], "source": "indeed"}
    finally:
        await client.close()


@router.get("/linkedin")
async def search_linkedin_jobs(q: str = Query(""), location: str = "", page: int = 1):
    client = LinkedInJobsClient()
    try:
        jobs = await client.search_jobs(query=q, location=location, page=page)
        return {"results": jobs, "source": "linkedin"}
    except Exception as e:
        logger.warning("linkedin_jobs_search_failed", error=str(e))
        return {"results": [], "source": "linkedin"}
    finally:
        await client.close()


@router.get("/geekhunter")
async def search_geekhunter(q: str = Query(""), page: int = 1):
    from modules.users.infrastructure.providers.geekhunter_client import GeekHunterClient
    client = GeekHunterClient()
    try:
        jobs = await client.search_jobs(query=q, page=page)
        return {"results": jobs, "source": "geekhunter"}
    except Exception as e:
        logger.warning("geekhunter_search_failed", error=str(e))
        return {"results": [], "source": "geekhunter"}
    finally:
        await client.close()


@router.get("/programathor")
async def search_programathor(q: str = Query(""), page: int = 1):
    from modules.users.infrastructure.providers.programathor_client import ProgramathorClient
    client = ProgramathorClient()
    try:
        jobs = await client.search_jobs(query=q, page=page)
        return {"results": jobs, "source": "programathor"}
    except Exception as e:
        logger.warning("programathor_search_failed", error=str(e))
        return {"results": [], "source": "programathor"}
    finally:
        await client.close()


@router.get("/search-all")
async def search_all(q: str = Query(""), page: int = 1):
    from asyncio import gather

    async def _remoteok():
        try:
            client = RemoteOKClient()
            r = await client.search_jobs(query=q, page=page)
            await client.close()
            return {"source": "remoteok", "jobs": r if isinstance(r, list) else []}
        except:
            return {"source": "remoteok", "jobs": []}

    async def _jobicy():
        try:
            client = JobicyClient()
            r = await client.search_jobs(query=q, page=page)
            await client.close()
            return {"source": "jobicy", "jobs": r}
        except:
            return {"source": "jobicy", "jobs": []}

    async def _google():
        try:
            client = GoogleJobsClient()
            r = await client.search_jobs(query=q, page=page)
            await client.close()
            return {"source": "google_jobs", "jobs": r}
        except:
            return {"source": "google_jobs", "jobs": []}

    results = await gather(_remoteok(), _jobicy(), _google(), return_exceptions=True)
    return {"results": [r for r in results if isinstance(r, dict) and r.get("jobs")]}


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
