"""Semantic job search API — embedding-based retrieval."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.config import settings
from core.database import get_db
from core.exceptions import NotFoundError, ValidationError
from core.models import JobEmbeddingModel, JobModel
from core.validators import validate_uuid
from modules.auth.api.dependencies import get_current_user
from modules.auth.domain.entities import User
from modules.search.infrastructure import EmbeddingService, rank_by_similarity

router = APIRouter(prefix="/search", tags=["search"])

DESCRIPTION_PREVIEW_CHARS = 300
CHUNK_PREVIEW_CHARS = 200
INDEXED_CHUNK_CHARS = 500


def _embedder() -> EmbeddingService:
    """Build the embedding service, using a real API only when configured."""
    return EmbeddingService(api_key=settings.EMBEDDING_API_KEY)


def _job_text(job: JobModel) -> str:
    """The text an embedding is built from — title carries the most signal."""
    company = job.company.name if job.company else ""
    return " ".join(
        part for part in (job.title, company, job.location, job.description) if part
    )


@router.get("/semantic")
async def semantic_search(
    q: str = Query("", max_length=1000),
    limit: int = Query(10, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rank indexed jobs by embedding similarity to the query."""
    if not q.strip():
        raise ValidationError("Informe um termo de busca")

    query_vector = await _embedder().embed_text(q)

    stored = (await db.execute(select(JobEmbeddingModel))).scalars().all()
    by_id = {str(row.job_id): row for row in stored}
    ranked = rank_by_similarity(
        query_vector, [(str(row.job_id), row.embedding or []) for row in stored], limit
    )
    if not ranked:
        return {"results": [], "query": q, "indexed_jobs": len(stored)}

    # One query for every hit: fetching jobs inside the ranking loop was an
    # N+1 that grew with the result limit.
    jobs = (
        (
            await db.execute(
                select(JobModel)
                .options(selectinload(JobModel.company))
                .where(JobModel.id.in_([job_id for job_id, _ in ranked]))
            )
        )
        .scalars()
        .all()
    )
    jobs_by_id = {str(job.id): job for job in jobs}

    results = []
    for job_id, score in ranked:
        job = jobs_by_id.get(job_id)
        if job is None:
            continue
        chunk = (by_id[job_id].chunk_text or "")[:CHUNK_PREVIEW_CHARS]
        results.append(
            {
                "id": str(job.id),
                "title": job.title or "",
                # `description` is nullable; slicing None used to raise a 500.
                "description": (job.description or "")[:DESCRIPTION_PREVIEW_CHARS],
                "company": job.company.name if job.company else "",
                "location": job.location or "",
                "apply_url": job.apply_url or "",
                "score": round(max(0.0, score) * 100, 1),
                "match": chunk,
            }
        )

    return {"results": results, "query": q, "indexed_jobs": len(stored)}


@router.post("/index-job/{job_id}")
async def index_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate and store the embedding for one job."""
    valid_id = validate_uuid(job_id, "job_id")
    job = (
        await db.execute(
            select(JobModel).options(selectinload(JobModel.company)).where(JobModel.id == valid_id)
        )
    ).scalar_one_or_none()
    if job is None:
        raise NotFoundError("Job not found")

    text = _job_text(job)
    vector = await _embedder().embed_text(text)

    existing = (
        await db.execute(
            select(JobEmbeddingModel).where(JobEmbeddingModel.job_id == valid_id)
        )
    ).scalar_one_or_none()

    if existing:
        existing.embedding = vector
        existing.chunk_text = text[:INDEXED_CHUNK_CHARS]
    else:
        db.add(
            JobEmbeddingModel(
                job_id=valid_id,
                embedding=vector,
                chunk_text=text[:INDEXED_CHUNK_CHARS],
            )
        )

    await db.flush()
    return {"status": "indexed", "job_id": valid_id, "vector_dim": len(vector)}
