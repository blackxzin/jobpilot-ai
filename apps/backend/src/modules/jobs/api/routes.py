"""Jobs API routes — local + multi-source."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.logger import get_logger
from modules.jobs.application.use_cases import SearchJobsUseCase, GetJobUseCase, SearchGupyUseCase
from modules.jobs.infrastructure.repositories import JobRepository
from modules.users.infrastructure.providers.gupy_client import GupyClient
from modules.users.infrastructure.providers.remoteok_client import RemoteOKClient
from modules.users.infrastructure.providers.programathor_client import ProgramathorClient
from modules.users.infrastructure.providers.geekhunter_client import GeekHunterClient

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


@router.get("/gupy")
async def search_gupy(
    q: str = Query("", alias="query"),
    location: str = "",
    remote: bool = False,
    page: int = 1,
):
    try:
        use_case = SearchGupyUseCase()
        return await use_case.execute(query=q, location=location, remote=remote, page=page)
    except Exception as e:
        logger.warning("gupy_search_failed", error=str(e))
        return {"error": "Gupy search failed", "detail": str(e)}


@router.get("/remoteok")
async def search_remoteok(q: str = Query(""), page: int = 1):
    client = RemoteOKClient()
    try:
        jobs = await client.search_jobs(query=q, page=page)
        return {"results": jobs, "source": "remoteok"}
    except Exception as e:
        logger.warning("remoteok_search_failed", error=str(e))
        return {"error": "RemoteOK search failed", "detail": str(e)}
    finally:
        await client.close()


@router.get("/programathor")
async def search_programathor(q: str = Query(""), page: int = 1):
    client = ProgramathorClient()
    try:
        jobs = await client.search_jobs(query=q, page=page)
        return {"results": jobs, "source": "programathor"}
    except Exception as e:
        logger.warning("programathor_search_failed", error=str(e))
        return {"error": "Programathor search failed", "detail": str(e)}
    finally:
        await client.close()


@router.get("/geekhunter")
async def search_geekhunter(q: str = Query(""), page: int = 1):
    client = GeekHunterClient()
    try:
        jobs = await client.search_jobs(query=q, page=page)
        return {"results": jobs, "source": "geekhunter"}
    except Exception as e:
        logger.warning("geekhunter_search_failed", error=str(e))
        return {"error": "GeekHunter search failed", "detail": str(e)}
    finally:
        await client.close()


@router.get("/search-all")
async def search_all(q: str = Query(""), page: int = 1):
    """Aggregate results from multiple sources."""
    from asyncio import gather

    async def _gupy():
        try:
            client = GupyClient()
            r = await client.search_jobs(query=q, page=page)
            await client.close()
            return {"source": "gupy", "jobs": r.get("jobs", []) if isinstance(r, dict) else r}
        except:
            return {"source": "gupy", "jobs": []}

    async def _remoteok():
        try:
            client = RemoteOKClient()
            r = await client.search_jobs(query=q, page=page)
            await client.close()
            return {"source": "remoteok", "jobs": r if isinstance(r, list) else []}
        except:
            return {"source": "remoteok", "jobs": []}

    results = await gather(_gupy(), _remoteok(), return_exceptions=True)
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
