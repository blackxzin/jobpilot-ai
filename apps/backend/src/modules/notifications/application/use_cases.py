"""Notification use cases."""
from __future__ import annotations

from datetime import datetime, UTC
from typing import Optional
from uuid import UUID

from modules.notifications.domain.entities import Notification
from modules.notifications.domain.enums import NotificationChannel, NotificationStatus
from modules.notifications.domain.repositories import INotificationRepository
from core.logger import get_logger

logger = get_logger(__name__)


class SendNotificationUseCase:
    """Sends a notification through the specified channel."""

    def __init__(self, repository: INotificationRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        user_id: str,
        type: NotificationChannel,
        title: str,
        message: str,
        channel: NotificationChannel,
    ) -> Notification:
        """Create and dispatch a notification.

        Args:
            user_id: The recipient user identifier.
            type: The notification category.
            title: Short headline.
            message: Body content.
            channel: The delivery channel to use.

        Returns:
            The persisted notification entity.
        """
        notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            channel=channel,
            status=NotificationStatus.PENDING,
        )

        logger.info(
            "send_notification_started",
            user_id=user_id,
            channel=channel.value,
            type=type.value,
        )

        try:
            # Dispatch through the channel-specific provider.
            # Each provider raises on failure so we can capture it below.
            await self._dispatch(notification)
            notification.mark_as_sent()
        except Exception as exc:
            logger.error(
                "send_notification_failed",
                user_id=user_id,
                channel=channel.value,
                error=str(exc),
            )
            notification.mark_as_failed()

        saved = await self._repository.create(notification)

        logger.info(
            "send_notification_completed",
            notification_id=str(saved.id),
            status=saved.status.value,
        )
        return saved

    async def _dispatch(self, notification: Notification) -> None:
        """Route the notification to the correct provider.

        The actual provider calls are delegated to infrastructure-level
        classes imported here to avoid circular dependencies at module load.
        """
        # Import inside method to keep domain layer free of infrastructure imports.
        from modules.notifications.infrastructure.providers.email_provider import (
            EmailNotificationProvider,
        )
        from modules.notifications.infrastructure.providers.discord_provider import (
            DiscordNotificationProvider,
        )
        from modules.notifications.infrastructure.providers.telegram_provider import (
            TelegramNotificationProvider,
        )
        from core.config import settings

        dispatch_map: dict[NotificationChannel, object] = {
            NotificationChannel.EMAIL: EmailNotificationProvider(
                api_key=settings.EMAIL_API_KEY,
                from_address=settings.EMAIL_FROM,
            ),
            NotificationChannel.DISCORD: DiscordNotificationProvider(),
            NotificationChannel.TELEGRAM: TelegramNotificationProvider(),
        }

        provider = dispatch_map.get(notification.channel)
        if provider is None:
            raise ValueError(f"Unsupported notification channel: {notification.channel}")

        await provider.send(notification)


class GetUserNotificationsUseCase:
    """Lists notifications for a specific user."""

    def __init__(self, repository: INotificationRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        user_id: str,
        *,
        status: Optional[NotificationStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        """Retrieve notifications for the given user.

        Args:
            user_id: The target user identifier.
            status: Optional status filter.
            limit: Maximum results to return.
            offset: Pagination offset.

        Returns:
            List of notification entities.
        """
        return await self._repository.get_for_user(
            user_id, status=status, limit=limit, offset=offset
        )


class MarkNotificationReadUseCase:
    """Marks a single notification as read."""

    def __init__(self, repository: INotificationRepository) -> None:
        self._repository = repository

    async def execute(self, notification_id: UUID) -> Optional[Notification]:
        """Mark the notification as read."""
        result = await self._repository.mark_as_read(notification_id)
        if result is None:
            logger.warning("mark_notification_read_not_found", notification_id=str(notification_id))
        return result


class GetUnreadCountUseCase:
    """Returns the count of unread notifications for a user."""

    def __init__(self, repository: INotificationRepository) -> None:
        self._repository = repository

    async def execute(self, user_id: str) -> int:
        """Count unread notifications for the user."""
        return await self._repository.get_unread_count(user_id)


class SendBulkNotificationsUseCase:
    """Sends notifications to multiple users (e.g., for new job alerts)."""

    def __init__(self, repository: INotificationRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        user_ids: list[str],
        type: NotificationChannel,
        title: str,
        message: str,
        channel: NotificationChannel,
    ) -> list[Notification]:
        """Dispatch notifications to every user in the list.

        Args:
            user_ids: Recipients.
            type: Notification category.
            title: Short headline.
            message: Body content.
            channel: Delivery channel.

        Returns:
            List of persisted notification entities.
        """
        send_use_case = SendNotificationUseCase(self._repository)
        results: list[Notification] = []

        for user_id in user_ids:
            notification = await send_use_case.execute(
                user_id=user_id,
                type=type,
                title=title,
                message=message,
                channel=channel,
            )
            results.append(notification)

        logger.info(
            "bulk_notifications_completed",
            count=len(results),
            channel=channel.value,
            type=type.value,
        )
        return results