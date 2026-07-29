"""Notification domain entity."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID, uuid4

from modules.notifications.domain.enums import NotificationChannel, NotificationStatus


@dataclass
class Notification:
    """Represents a single notification dispatched to a user.

    Attributes:
        id: Unique identifier.
        user_id: Target user identifier.
        type: Category of notification (email, discord, telegram, push).
        title: Short headline for the notification.
        message: Full body content.
        channel: Delivery channel.
        status: Current lifecycle state.
        read_at: Timestamp when the user marked it as read (nullable).
        created_at: When the notification was created.
    """

    id: UUID = field(default_factory=uuid4)
    user_id: str = ""
    type: NotificationChannel = NotificationChannel.EMAIL
    title: str = ""
    message: str = ""
    channel: NotificationChannel = NotificationChannel.EMAIL
    status: NotificationStatus = NotificationStatus.PENDING
    read_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def mark_as_read(self) -> None:
        """Transition the notification to the read state."""
        self.status = NotificationStatus.READ
        self.read_at = datetime.now(UTC)

    def mark_as_sent(self) -> None:
        """Transition the notification to the sent state."""
        self.status = NotificationStatus.SENT

    def mark_as_failed(self) -> None:
        """Transition the notification to the failed state."""
        self.status = NotificationStatus.FAILED