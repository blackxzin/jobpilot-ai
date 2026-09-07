"""Celery application configuration for JobPilot AI."""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from core.config import settings

celery_app = Celery(
    "jobpilot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "workers.scraping",
        "workers.matching",
        "workers.ats_scoring",
        "workers.email_notifications",
        "workers.auto_apply",
    ],
)

# Without a schedule the celery-beat service in docker-compose starts, connects
# to Redis, and then sits idle forever — the "scheduled scraping" the docs
# promised never ran.
celery_app.conf.beat_schedule = {
    "refresh-job-board": {
        "task": "workers.scraping.scrape_all_sources",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    "deliver-pending-notifications": {
        "task": "workers.email_notifications.deliver_pending_notifications",
        "schedule": crontab(minute="*/5"),
    },
}

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_max_tasks_per_child=200,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
