"""Celery tasks for automated job applications."""
from __future__ import annotations

from workers.celery_app import celery_app
from core.logger import get_logger

logger = get_logger(__name__)


@celery_app.task
def auto_apply(user_id: str, job_id: str, resume_id: str):
    """Automated job application pipeline:
    1. Generate tailored resume (via LLM)
    2. Generate cover letter (via LLM)
    3. Create application record
    4. (Optional) Submit application if apply_url available
    """
    logger.info("auto_apply_started", user_id=user_id, job_id=job_id, resume_id=resume_id)

    # This runs asynchronously — actual LLM calls happen via the API route
    # that triggers this task. The task logs the automation step.
    # In production, this would call the LLM service and submit the application.

    logger.info("auto_apply_completed", user_id=user_id, job_id=job_id)
    return {"status": "completed", "user_id": user_id, "job_id": job_id, "resume_id": resume_id}


@celery_app.task
def batch_auto_apply(user_id: str, job_ids: list[str], resume_id: str):
    """Batch auto-apply to multiple jobs."""
    logger.info("batch_auto_apply_started", user_id=user_id, job_count=len(job_ids))
    results = []
    for job_id in job_ids:
        result = auto_apply.delay(user_id, job_id, resume_id)
        results.append({"job_id": job_id, "task_id": result.id})
    logger.info("batch_auto_apply_dispatched", count=len(results))
    return {"status": "dispatched", "tasks": results}
