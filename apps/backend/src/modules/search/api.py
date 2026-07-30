"""Vector search API — semantic job matching."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from core.database import get_db
from core.models import JobModel, JobEmbeddingModel
from modules.auth.infrastructure.repositories import SQLAlchemyUserRepository, SQLAlchemySessionRepository
from modules.auth.application.use_cases import GetCurrentUserUseCase
from modules.search.infrastructure import EmbeddingService, cosine_similarity
from core.exceptions import NotFoundError

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/semantic")
async def semantic_search(
    q: str = Query(""),
    limit: int = 10,
    authorization: str = Header(""),
    db: AsyncSession = Depends(get_db),
):
    """Semantic job search using embeddings."""
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    await auth_uc.execute(token)

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
async def index_job(job_id: str, authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    """Generate and store embedding for a specific job."""
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    await auth_uc.execute(token)

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
