"""Celery tasks for email notifications."""
from __future__ import annotations

from workers.celery_app import celery_app
from core.logger import get_logger

logger = get_logger(__name__)


@celery_app.task
def send_email_notification(to: str, subject: str, body: str):
    """Send an email notification."""
    logger.info("email_notification_task", to=to, subject=subject)
    # TODO: implement with Resend/SendGrid
    return {"status": "completed", "to": to}
