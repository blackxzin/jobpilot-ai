"""Notification repository interfaces."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Optional
from uuid import UUID

from modules.notifications.domain.entities import Notification
from modules.notifications.domain.enums import NotificationStatus


class INotificationRepository(ABC):
    """Abstract contract for notification persistence."""

    @abstractmethod
    async def create(self, notification: Notification) -> Notification:
        """Persist a new notification and return it with its database ID.

        Args:
            notification: The notification entity to persist.

        Returns:
            The persisted notification, possibly with an assigned ID.
        """
        ...

    @abstractmethod
    async def get_for_user(
        self,
        user_id: str,
        *,
        status: Optional[NotificationStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        """Retrieve notifications for a given user, optionally filtered by status.

        Args:
            user_id: The target user identifier.
            status: Optional status filter; when None, returns all.
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            A list of notification entities ordered by creation date descending.
        """
        ...

    @abstractmethod
    async def mark_as_read(self, notification_id: UUID) -> Optional[Notification]:
        """Mark a notification as read.

        Args:
            notification_id: The notification to update.

        Returns:
            The updated notification, or None if not found.
        """
        ...

    @abstractmethod
    async def get_unread_count(self, user_id: str) -> int:
        """Count unread notifications for a user.

        Args:
            user_id: The target user identifier.

        Returns:
            The number of notifications in the PENDING or SENT state.
        """
        ...