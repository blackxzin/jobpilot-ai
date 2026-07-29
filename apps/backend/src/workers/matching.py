"""Celery tasks for job-resume matching."""
from __future__ import annotations

from workers.celery_app import celery_app
from core.logger import get_logger

logger = get_logger(__name__)


@celery_app.task
def run_matching(resume_id: str):
    """Run AI matching between a resume and all active jobs."""
    logger.info("matching_started", resume_id=resume_id)
    # TODO: implement matching logic with LLMService
    return {"status": "completed", "resume_id": resume_id, "matches": []}
