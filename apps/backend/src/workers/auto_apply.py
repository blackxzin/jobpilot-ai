"""Celery task that runs the tailored-resume + cover-letter pipeline offline.

The API route generates both documents inline so the user sees them straight
away. This task exists for the batch path: applying to a shortlist of jobs
without holding an HTTP request open for one LLM call per job.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.logger import get_logger
from core.models import ApplicationModel, CoverLetterModel, JobModel, ResumeModel
from modules.ai.infrastructure.llm_providers.offline_provider import OfflineProvider
from workers.celery_app import celery_app
from workers.runtime import run_async, worker_session

logger = get_logger(__name__)


def _job_dict(job: JobModel) -> dict:
    return {
        "title": job.title or "",
        "company": job.company.name if job.company else "",
        "description": job.description or "",
        "requirements": [r.requirement for r in (job.requirements or [])],
    }


async def _apply(user_id: str, job_id: str, resume_id: str) -> dict:
    async with worker_session() as session:
        job = (
            await session.execute(
                select(JobModel)
                .options(selectinload(JobModel.company), selectinload(JobModel.requirements))
                .where(JobModel.id == job_id)
            )
        ).scalar_one_or_none()
        resume = (
            await session.execute(select(ResumeModel).where(ResumeModel.id == resume_id))
        ).scalar_one_or_none()

        if job is None or resume is None:
            logger.warning("auto_apply_missing_input", job_id=job_id, resume_id=resume_id)
            return {"status": "not_found", "job_id": job_id, "resume_id": resume_id}

        already = (
            await session.execute(
                select(ApplicationModel.id).where(
                    ApplicationModel.user_id == user_id, ApplicationModel.job_id == job_id
                )
            )
        ).first()
        if already:
            logger.info("auto_apply_skipped_duplicate", job_id=job_id, user_id=user_id)
            return {"status": "already_applied", "job_id": job_id}

        analyzer = OfflineProvider()
        job_payload = _job_dict(job)
        cover = await analyzer.generate_cover_letter(resume.content_text or "", job_payload)

        session.add(
            CoverLetterModel(
                user_id=user_id,
                job_id=job_id,
                title=f"{job.title} — {job_payload['company']}".strip(" —"),
                content=cover,
            )
        )
        application = ApplicationModel(
            job_id=job_id,
            resume_id=resume_id,
            user_id=user_id,
            status="applied",
            cover_letter=cover,
            custom_message="Auto-applied via JobPilot AI",
            source_platform="auto_apply",
            applied_at=datetime.now(UTC),
        )
        session.add(application)
        await session.flush()
        application_id = str(application.id)

    logger.info("auto_apply_completed", user_id=user_id, job_id=job_id)
    return {"status": "completed", "application_id": application_id, "job_id": job_id}


@celery_app.task(name="workers.auto_apply.auto_apply")
def auto_apply(user_id: str, job_id: str, resume_id: str) -> dict:
    """Generate a cover letter and record an application for one job."""
    return run_async(lambda: _apply(user_id, job_id, resume_id))


@celery_app.task(name="workers.auto_apply.batch_auto_apply")
def batch_auto_apply(user_id: str, job_ids: list[str], resume_id: str) -> dict:
    """Fan out `auto_apply` across a shortlist of jobs."""
    tasks = [auto_apply.delay(user_id, job_id, resume_id).id for job_id in job_ids]
    logger.info("batch_auto_apply_dispatched", user_id=user_id, count=len(tasks))
    return {"status": "dispatched", "task_ids": tasks}
