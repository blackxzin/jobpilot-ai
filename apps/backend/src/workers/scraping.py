"""Celery tasks that ingest jobs from external boards into the local database.

Previously these tasks logged a line and returned — the two Celery services in
docker-compose ran permanently doing nothing, while the README advertised
scheduled scraping. They now fetch, de-duplicate and persist real postings,
then index them for semantic search.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select

from core.logger import get_logger
from core.models import CompanyModel, JobEmbeddingModel, JobModel
from modules.search.infrastructure import EmbeddingService
from workers.celery_app import celery_app
from workers.runtime import run_async, worker_session

logger = get_logger(__name__)

# Boards that need no credentials, so scheduled scraping works out of the box.
FREE_SOURCES = ("remoteok", "jobicy")

# Default queries to keep the board populated when the task runs unattended.
DEFAULT_QUERIES = ("python", "backend", "frontend", "fullstack", "devops")


def _client_for(source: str):
    if source == "remoteok":
        from modules.users.infrastructure.providers.remoteok_client import RemoteOKClient

        return RemoteOKClient()
    if source == "jobicy":
        from modules.users.infrastructure.providers.jobicy_client import JobicyClient

        return JobicyClient()
    if source == "gupy":
        from modules.users.infrastructure.providers.gupy_client import GupyClient

        return GupyClient()
    raise ValueError(f"Unsupported job source: {source}")


async def _get_or_create_company(session, name: str) -> CompanyModel | None:
    clean = (name or "").strip()
    if not clean:
        return None
    existing = (
        await session.execute(
            select(CompanyModel).where(func.lower(CompanyModel.name) == clean.lower())
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    company = CompanyModel(name=clean)
    session.add(company)
    await session.flush()
    return company


async def _persist(session, source: str, postings: list[dict]) -> int:
    """Insert postings not already stored. Returns how many were new."""
    embedder = EmbeddingService()
    created = 0

    for posting in postings:
        source_id = str(posting.get("id") or posting.get("source_id") or "").strip()
        title = (posting.get("title") or "").strip()
        if not title:
            continue

        # De-duplicate on (source, source_id); re-running the task must not
        # multiply the same posting on every schedule tick.
        if source_id:
            duplicate = (
                await session.execute(
                    select(JobModel.id).where(
                        JobModel.source == source, JobModel.source_id == source_id
                    )
                )
            ).first()
            if duplicate:
                continue

        company = await _get_or_create_company(session, posting.get("company") or "")
        job = JobModel(
            source=source,
            source_id=source_id or None,
            title=title[:255],
            company_id=company.id if company else None,
            description=posting.get("description") or "",
            location=(posting.get("location") or "")[:255],
            location_type="remote" if posting.get("is_remote") else "",
            is_remote=bool(posting.get("is_remote")),
            apply_url=(posting.get("apply_url") or posting.get("url") or "")[:512],
            source_url=(posting.get("url") or "")[:512],
            posted_at=datetime.now(UTC),
        )
        session.add(job)
        await session.flush()

        text = " ".join(filter(None, [job.title, posting.get("company") or "", job.description]))
        session.add(
            JobEmbeddingModel(
                job_id=job.id,
                embedding=await embedder.embed_text(text),
                chunk_text=text[:500],
            )
        )
        created += 1

    return created


async def _scrape(source: str, query: str) -> dict:
    client = _client_for(source)
    try:
        postings = await client.search_jobs(query=query)
    except Exception as e:
        # One unreachable board must not fail the whole scheduled run.
        logger.warning("scrape_source_failed", source=source, query=query, error=str(e))
        return {"source": source, "query": query, "imported": 0, "error": str(e)}
    finally:
        await client.close()

    async with worker_session() as session:
        imported = await _persist(session, source, postings if isinstance(postings, list) else [])

    logger.info("scrape_source_done", source=source, query=query, imported=imported)
    return {"source": source, "query": query, "imported": imported}


@celery_app.task(name="workers.scraping.scrape_source")
def scrape_source(source: str, query: str = "") -> dict:
    """Import jobs from one board for one query."""
    return run_async(lambda: _scrape(source, query))


@celery_app.task(name="workers.scraping.scrape_all_sources")
def scrape_all_sources(queries: list[str] | None = None) -> dict:
    """Import jobs from every credential-free board, for each default query."""
    terms = queries or list(DEFAULT_QUERIES)
    results = [
        scrape_source.delay(source, query).id for source in FREE_SOURCES for query in terms
    ]
    logger.info("scrape_all_dispatched", tasks=len(results))
    return {"status": "dispatched", "task_count": len(results), "sources": list(FREE_SOURCES)}
