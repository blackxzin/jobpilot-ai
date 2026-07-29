"""Notification channel and status enumerations."""
from __future__ import annotations

from enum import Enum


class NotificationChannel(str, Enum):
    """Supported notification delivery channels."""

    EMAIL = "email"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    PUSH = "push"


class NotificationStatus(str, Enum):
    """Lifecycle states of a notification."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    READ = "read"