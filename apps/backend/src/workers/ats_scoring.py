"""Celery task that computes and stores a resume's standalone ATS score.

`resumes.ats_score` is read by the dashboard and the analytics overview but was
never written, so the average ATS figure was permanently null.
"""
from __future__ import annotations

from sqlalchemy import select

from core.logger import get_logger
from core.models import ResumeModel
from modules.ai.infrastructure.llm_providers.offline_provider import OfflineProvider
from workers.celery_app import celery_app
from workers.runtime import run_async, worker_session

logger = get_logger(__name__)

async def _score(resume_id: str) -> dict:
    async with worker_session() as session:
        resume = (
            await session.execute(select(ResumeModel).where(ResumeModel.id == resume_id))
        ).scalar_one_or_none()
        if resume is None:
            logger.warning("ats_scoring_resume_not_found", resume_id=resume_id)
            return {"status": "not_found", "resume_id": resume_id}

        # Empty job description on purpose: this is the standalone score shown
        # on the resume card, so it audits the document rather than measuring
        # fit against one particular posting.
        analysis = await OfflineProvider().analyze_resume(resume.content_text or "", "")
        resume.ats_score = int(analysis.get("score") or 0)
        resume.ats_breakdown = {
            "matched_skills": analysis.get("matched_skills", []),
            "missing_skills": analysis.get("missing_skills", []),
            "suggestions": analysis.get("suggestions", []),
            "strengths": analysis.get("strengths", []),
        }
        score = resume.ats_score

    logger.info("ats_scoring_completed", resume_id=resume_id, score=score)
    return {"status": "completed", "resume_id": resume_id, "score": score}


@celery_app.task(name="workers.ats_scoring.score_resume")
def score_resume(resume_id: str) -> dict:
    """Compute and persist the ATS score for one resume."""
    return run_async(lambda: _score(resume_id))
