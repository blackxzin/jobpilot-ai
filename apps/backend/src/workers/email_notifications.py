"""Celery task that delivers pending notifications and retries failed ones.

Notifications are written to the database with status `pending` by the request
that triggers them. Delivering them here keeps a slow or down provider from
blocking an HTTP response, and gives failed sends a retry path — previously
nothing ever read the pending rows.
"""
from __future__ import annotations

from sqlalchemy import select

from core.logger import get_logger
from core.models import NotificationModel, UserModel
from modules.notifications.infrastructure.providers import (
    DiscordNotificationProvider,
    EmailNotificationProvider,
    TelegramNotificationProvider,
)
from workers.celery_app import celery_app
from workers.runtime import run_async, worker_session

logger = get_logger(__name__)

# Bounded so one run cannot hold a worker for an unbounded time.
MAX_PER_RUN = 100

_PROVIDERS = {
    "email": EmailNotificationProvider,
    "discord": DiscordNotificationProvider,
    "telegram": TelegramNotificationProvider,
}


class _Dispatchable:
    """Adapter giving a database row the shape the providers expect."""

    def __init__(self, row: NotificationModel, recipient: str):
        self.title = row.title
        self.message = row.message
        self.recipient = recipient


async def _deliver_pending(limit: int) -> dict:
    sent = failed = 0

    async with worker_session() as session:
        pending = (
            (
                await session.execute(
                    select(NotificationModel)
                    .where(NotificationModel.status == "pending")
                    .order_by(NotificationModel.created_at)
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        if not pending:
            return {"status": "completed", "sent": 0, "failed": 0}

        # Resolve every recipient in one query rather than per notification.
        user_ids = {row.user_id for row in pending}
        emails = dict(
            (
                await session.execute(
                    select(UserModel.id, UserModel.email).where(UserModel.id.in_(user_ids))
                )
            ).all()
        )

        for row in pending:
            provider_cls = _PROVIDERS.get(row.channel)
            if provider_cls is None:
                logger.warning("notification_unknown_channel", channel=row.channel, id=row.id)
                row.status = "failed"
                failed += 1
                continue
            try:
                await provider_cls().send(_Dispatchable(row, emails.get(row.user_id, "")))
                row.status = "sent"
                sent += 1
            except Exception as e:
                # Left as `pending` on purpose so the next run retries it.
                logger.warning("notification_delivery_failed", id=row.id, error=str(e))
                failed += 1

    logger.info("notifications_delivered", sent=sent, failed=failed)
    return {"status": "completed", "sent": sent, "failed": failed}


@celery_app.task(name="workers.email_notifications.deliver_pending_notifications")
def deliver_pending_notifications(limit: int = MAX_PER_RUN) -> dict:
    """Deliver notifications still sitting in `pending`."""
    return run_async(lambda: _deliver_pending(limit))
