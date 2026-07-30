"""Notification infrastructure providers — email (Resend), discord, telegram."""
from __future__ import annotations

from typing import Any

import httpx

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


class EmailNotificationProvider:
    """Send emails via Resend API. Falls back to log if no API key set."""

    def __init__(self, api_key: str = "", from_address: str = ""):
        self._api_key = api_key or settings.EMAIL_API_KEY
        self._from = from_address or settings.EMAIL_FROM

    async def send(self, notification: Any) -> None:
        if not self._api_key or self._api_key in ("", "sk-placeholder"):
            logger.info("email_notification_skipped", to=notification.user_id, title=notification.title, reason="no_api_key")
            return

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": self._from,
                    "to": notification.user_id,  # In production, resolve user email
                    "subject": notification.title,
                    "text": notification.message,
                },
            )
            if resp.is_success:
                logger.info("email_sent", to=notification.user_id, subject=notification.title)
            else:
                logger.error("email_failed", to=notification.user_id, status=resp.status_code, detail=resp.text)
                raise RuntimeError(f"Resend API error: {resp.status_code} {resp.text}")


class DiscordNotificationProvider:
    """Send notifications via Discord webhook. Configure webhook URL in env."""

    def __init__(self, webhook_url: str = ""):
        self._webhook_url = webhook_url or getattr(settings, "DISCORD_WEBHOOK_URL", "")

    async def send(self, notification: Any) -> None:
        if not self._webhook_url:
            logger.info("discord_notification_skipped", title=notification.title, reason="no_webhook_url")
            return

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                self._webhook_url,
                json={
                    "content": f"**{notification.title}**\n{notification.message[:2000]}",
                    "username": "JobPilot AI",
                },
            )
            if resp.is_success:
                logger.info("discord_sent", title=notification.title)
            else:
                logger.error("discord_failed", status=resp.status_code, detail=resp.text)


class TelegramNotificationProvider:
    """Send notifications via Telegram Bot API. Configure bot token + chat ID in env."""

    def __init__(self, bot_token: str = "", chat_id: str = ""):
        self._bot_token = bot_token or getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        self._chat_id = chat_id or getattr(settings, "TELEGRAM_CHAT_ID", "")

    async def send(self, notification: Any) -> None:
        if not self._bot_token or not self._chat_id:
            logger.info("telegram_notification_skipped", title=notification.title, reason="no_bot_config")
            return

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{self._bot_token}/sendMessage",
                json={
                    "chat_id": self._chat_id,
                    "text": f"*{notification.title}*\n{notification.message}",
                    "parse_mode": "Markdown",
                },
            )
            if resp.is_success:
                logger.info("telegram_sent", title=notification.title)
            else:
                logger.error("telegram_failed", status=resp.status_code, detail=resp.text)
