"""Celery tasks that score a resume against stored jobs and persist matches.

The `job_matches` table and its full schema already existed but nothing ever
wrote a row: matching only ran inline, per request, and the result was thrown
away. Running it in the background lets a user upload a CV and come back to a
ranked list.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.logger import get_logger
from core.models import JobMatchModel, JobModel, ResumeModel
from modules.ai.infrastructure.llm_providers.offline_provider import OfflineProvider
from workers.celery_app import celery_app
from workers.runtime import run_async, worker_session

logger = get_logger(__name__)

# Cap on jobs scored per run. Matching every job for every resume is O(n*m);
# the newest postings are the ones worth surfacing.
MAX_JOBS_PER_RUN = 500

# Below this, a "match" is noise the user should not be shown.
MIN_STORED_SCORE = 30


async def _run_matching(resume_id: str, limit: int) -> dict:
    async with worker_session() as session:
        resume = (
            await session.execute(select(ResumeModel).where(ResumeModel.id == resume_id))
        ).scalar_one_or_none()
        if resume is None:
            logger.warning("matching_resume_not_found", resume_id=resume_id)
            return {"status": "not_found", "resume_id": resume_id, "matches": 0}

        jobs = (
            (
                await session.execute(
                    select(JobModel)
                    .options(selectinload(JobModel.company), selectinload(JobModel.requirements))
                    .where(JobModel.is_active.is_(True))
                    .order_by(JobModel.created_at.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )

        # The offline analyzer is used deliberately: batch matching against
        # hundreds of jobs through a hosted LLM would be slow and expensive,
        # and lexical overlap is a reasonable first-pass filter.
        analyzer = OfflineProvider()
        existing_job_ids = {
            row[0]
            for row in await session.execute(
                select(JobMatchModel.job_id).where(JobMatchModel.resume_id == resume_id)
            )
        }

        stored = 0
        for job in jobs:
            if str(job.id) in {str(j) for j in existing_job_ids}:
                continue
            result = await analyzer.compare_job(
                resume.content_text or "",
                {
                    "title": job.title or "",
                    "company": job.company.name if job.company else "",
                    "description": job.description or "",
                    "requirements": [r.requirement for r in (job.requirements or [])],
                },
            )
            score = float(result.get("compatibility_score") or 0)
            if score < MIN_STORED_SCORE:
                continue

            reasons = result.get("match_reasons") or []
            session.add(
                JobMatchModel(
                    job_id=job.id,
                    resume_id=resume_id,
                    score=score,
                    match_reasons=reasons,
                    suggestions=result.get("suggestions") or [],
                    matched_skills=[r["text"] for r in reasons if r.get("type") == "match"],
                    missing_skills=[r["text"] for r in reasons if r.get("type") == "gap"],
                    score_details={"analyzer": analyzer.provider_name},
                )
            )
            stored += 1

    logger.info("matching_completed", resume_id=resume_id, matches=stored, scanned=len(jobs))
    return {"status": "completed", "resume_id": resume_id, "matches": stored, "scanned": len(jobs)}


@celery_app.task(name="workers.matching.run_matching")
def run_matching(resume_id: str, limit: int = MAX_JOBS_PER_RUN) -> dict:
    """Score one resume against the most recent active jobs."""
    return run_async(lambda: _run_matching(resume_id, limit))
