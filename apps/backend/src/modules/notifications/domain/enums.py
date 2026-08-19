"""Notification channel and status enumerations."""
from __future__ import annotations

from enum import StrEnum


class NotificationChannel(StrEnum):
    """Supported notification delivery channels."""

    EMAIL = "email"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    PUSH = "push"


class NotificationStatus(StrEnum):
    """Lifecycle states of a notification."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    READ = "read"