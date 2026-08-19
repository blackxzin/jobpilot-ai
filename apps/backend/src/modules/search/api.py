"""Vector search API — semantic job matching."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.exceptions import NotFoundError
from core.models import JobEmbeddingModel, JobModel
from modules.auth.api.dependencies import get_current_user
from modules.auth.domain.entities import User
from modules.search.infrastructure import EmbeddingService, cosine_similarity

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/semantic")
async def semantic_search(
    q: str = Query(""),
    limit: int = Query(10, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Semantic job search using embeddings."""
    # 1. Generate embedding for query
    embedder = EmbeddingService()
    query_vec = await embedder.embed_text(q)

    # 2. Fetch all job embeddings
    result = await db.execute(select(JobEmbeddingModel))
    stored = result.scalars().all()

    # 3. Score by cosine similarity
    scored = []
    for se in stored:
        if not se.embedding:
            continue
        sim = await cosine_similarity(query_vec, se.embedding)
        scored.append((sim, se.job_id, se.chunk_text or ""))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:limit]

    # 4. Fetch job details for matches
    jobs = []
    for sim, job_id, chunk in top:
        job = await db.get(JobModel, job_id)
        if job:
            jobs.append({
                "id": str(job.id),
                "title": job.title,
                "description": job.description[:300],
                "company": str(job.company_id) if job.company_id else "",
                "location": job.location,
                "score": round(sim * 100, 1),
                "match": chunk[:200],
            })

    return {"results": jobs, "query": q}


@router.post("/index-job/{job_id}")
async def index_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate and store embedding for a specific job."""
    job = await db.get(JobModel, job_id)
    if not job:
        raise NotFoundError("Job not found")

    embedder = EmbeddingService()
    text_to_embed = f"{job.title} {job.description} {job.location}"
    vec = await embedder.embed_text(text_to_embed)

    # Upsert
    existing = await db.execute(
        select(JobEmbeddingModel).where(JobEmbeddingModel.job_id == job_id)
    )
    existing_emb = existing.scalar_one_or_none()
    if existing_emb:
        existing_emb.embedding = vec
        existing_emb.chunk_text = text_to_embed[:500]
    else:
        import uuid
        emb = JobEmbeddingModel(
            id=str(uuid.uuid4()),
            job_id=job_id,
            embedding=vec,
            chunk_text=text_to_embed[:500],
        )
        db.add(emb)

    await db.flush()
    return {"status": "indexed", "job_id": job_id, "vector_dim": len(vec)}
