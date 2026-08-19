"""Notifications API routes."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.exceptions import NotFoundError, ValidationError
from modules.auth.api.dependencies import ensure_owner, get_current_user
from modules.auth.domain.entities import User
from modules.notifications.application.use_cases import (
    GetUserNotificationsUseCase,
    MarkNotificationReadUseCase,
)
from modules.notifications.infrastructure.repositories import SQLAlchemyNotificationRepository

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    use_case = GetUserNotificationsUseCase(SQLAlchemyNotificationRepository(db))
    results = await use_case.execute(user_id=str(user.id), limit=limit, offset=offset)
    return {"results": [_n_to_dict(n) for n in results]}


@router.get("/unread-count")
async def unread_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SQLAlchemyNotificationRepository(db)
    count = await repo.get_unread_count(str(user.id))
    return {"unread_count": count}


@router.patch("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        notification_uuid = UUID(notification_id)
    except (ValueError, AttributeError, TypeError) as e:
        raise ValidationError("notification_id must be a valid UUID") from e

    repo = SQLAlchemyNotificationRepository(db)
    existing = await repo.get_by_id(notification_uuid)
    if existing is None:
        raise NotFoundError("Notification not found")
    ensure_owner(existing.user_id, user, "Notification")

    use_case = MarkNotificationReadUseCase(repo)
    result = await use_case.execute(notification_uuid)
    if result is None:
        raise NotFoundError("Notification not found")
    return _n_to_dict(result)


def _n_to_dict(n) -> dict:
    return {
        "id": str(n.id),
        "title": n.title,
        "message": n.message[:200],
        "channel": n.channel.value if hasattr(n.channel, "value") else n.channel,
        "status": n.status.value if hasattr(n.status, "value") else n.status,
        "read_at": str(n.read_at) if n.read_at else None,
        "created_at": str(n.created_at),
    }
