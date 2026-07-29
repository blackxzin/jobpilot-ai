"""Celery tasks for job scraping."""
from __future__ import annotations

from workers.celery_app import celery_app
from core.logger import get_logger

logger = get_logger(__name__)


@celery_app.task
def scrape_gupy_jobs(query: str = "", location: str = ""):
    """Scrape jobs from Gupy API."""
    logger.info("scrape_gupy_jobs_started", query=query, location=location)
    # TODO: implement with GupyClient
    return {"status": "completed", "source": "gupy", "query": query}


@celery_app.task
def scrape_all_sources():
    """Scrape all configured job sources."""
    logger.info("scrape_all_sources_started")
    return {"status": "completed"}
