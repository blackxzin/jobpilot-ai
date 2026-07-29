"""Notifications API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from modules.auth.infrastructure.repositories import SQLAlchemyUserRepository, SQLAlchemySessionRepository
from modules.auth.application.use_cases import GetCurrentUserUseCase
from modules.notifications.infrastructure.repositories import SQLAlchemyNotificationRepository
from modules.notifications.application.use_cases import (
    GetUserNotificationsUseCase, MarkNotificationReadUseCase, GetUnreadCountUseCase,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    limit: int = 50, offset: int = 0,
    authorization: str = Header(""),
    db: AsyncSession = Depends(get_db),
):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    user = await auth_uc.execute(token)

    use_case = GetUserNotificationsUseCase(SQLAlchemyNotificationRepository(db))
    results = await use_case.execute(user_id=str(user.id), limit=limit, offset=offset)
    return {"results": [_n_to_dict(n) for n in results]}


@router.get("/unread-count")
async def unread_count(authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    user = await auth_uc.execute(token)

    repo = SQLAlchemyNotificationRepository(db)
    count = await repo.get_unread_count(str(user.id))
    return {"unread_count": count}


@router.patch("/{notification_id}/read")
async def mark_read(notification_id: str, authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    await auth_uc.execute(token)

    from uuid import UUID
    use_case = MarkNotificationReadUseCase(SQLAlchemyNotificationRepository(db))
    result = await use_case.execute(UUID(notification_id))
    if result:
        return _n_to_dict(result)
    return {"message": "Notification not found"}


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
