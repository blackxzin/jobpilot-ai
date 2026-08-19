"""Celery tasks for ATS scoring."""
from __future__ import annotations

from core.logger import get_logger
from workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task
def calculate_ats_score(resume_id: str):
    """Calculate ATS score for a resume."""
    logger.info("ats_scoring_started", resume_id=resume_id)
    # TODO: implement scoring logic
    return {"status": "completed", "resume_id": resume_id, "score": 0}
