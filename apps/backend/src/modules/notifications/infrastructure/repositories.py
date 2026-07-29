"""Notifications infrastructure — SQLAlchemy repository."""
from __future__ import annotations

from typing import Optional
from uuid import UUID
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import NotificationModel
from modules.notifications.domain.entities import Notification
from modules.notifications.domain.enums import NotificationStatus
from modules.notifications.domain.repositories import INotificationRepository


class SQLAlchemyNotificationRepository(INotificationRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, notification: Notification) -> Notification:
        import uuid
        model = NotificationModel(
            id=str(uuid.uuid4()),
            user_id=notification.user_id,
            type=notification.type.value if hasattr(notification.type, "value") else notification.type,
            title=notification.title,
            message=notification.message,
            channel=notification.channel.value if hasattr(notification.channel, "value") else notification.channel,
            status=notification.status.value if hasattr(notification.status, "value") else notification.status,
            read_at=notification.read_at,
        )
        self._session.add(model)
        await self._session.flush()
        notification.id = UUID(model.id)
        return notification

    async def get_for_user(self, user_id: str, *, status: Optional[NotificationStatus] = None, limit: int = 50, offset: int = 0) -> list[Notification]:
        stmt = select(NotificationModel).where(NotificationModel.user_id == user_id)
        if status:
            stmt = stmt.where(NotificationModel.status == status.value)
        stmt = stmt.order_by(NotificationModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def mark_as_read(self, notification_id: UUID) -> Optional[Notification]:
        from datetime import datetime, UTC
        result = await self._session.execute(
            update(NotificationModel).where(NotificationModel.id == str(notification_id)).values(status="read", read_at=datetime.now(UTC)).returning(NotificationModel)
        )
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def get_unread_count(self, user_id: str) -> int:
        result = await self._session.execute(
            select(func.count()).where(NotificationModel.user_id == user_id, NotificationModel.status.in_(["pending", "sent"]))
        )
        return result.scalar() or 0

    def _to_domain(self, model: NotificationModel) -> Notification:
        from uuid import UUID
        return Notification(
            id=UUID(model.id) if isinstance(model.id, str) else model.id,
            user_id=model.user_id,
            title=model.title,
            message=model.message,
            channel=model.channel,
            status=model.status,
            read_at=model.read_at,
            created_at=model.created_at,
        )
