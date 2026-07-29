"""Notification infrastructure providers — email, discord, telegram."""
from __future__ import annotations

from typing import Any
import smtplib
from email.mime.text import MIMEText

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


class EmailNotificationProvider:
    def __init__(self, api_key: str = "", from_address: str = ""):
        self._api_key = api_key or settings.EMAIL_API_KEY
        self._from = from_address or settings.EMAIL_FROM

    async def send(self, notification: Any) -> None:
        logger.info("email_notification", to=notification.user_id, title=notification.title)
        # In production, use Resend/SendGrid API.
        # For MVP, log the notification.
        logger.info("email_sent", to=notification.user_id, subject=notification.title)


class DiscordNotificationProvider:
    async def send(self, notification: Any) -> None:
        logger.info("discord_notification", user_id=notification.user_id, title=notification.title)


class TelegramNotificationProvider:
    async def send(self, notification: Any) -> None:
        logger.info("telegram_notification", user_id=notification.user_id, title=notification.title)
