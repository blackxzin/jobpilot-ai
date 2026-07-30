"""Tests for notification module — CRUD + providers."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import NotificationModel


@pytest.mark.asyncio
async def test_notifications_list(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "notif@test.com", "password": "pass12345"})
    token = reg.json()["token"]

    r = await client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert "results" in data


@pytest.mark.asyncio
async def test_notifications_unread_count(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "notif2@test.com", "password": "pass12345"})
    token = reg.json()["token"]

    r = await client.get("/api/v1/notifications/unread-count", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "unread_count" in r.json()


@pytest.mark.asyncio
async def test_notifications_mark_read(client: AsyncClient, db_session: AsyncSession):
    import uuid
    from datetime import datetime, UTC

    reg = await client.post("/api/v1/auth/register", json={"email": "notif3@test.com", "password": "pass12345"})
    token = reg.json()["token"]
    user_id = reg.json()["user_id"]

    # Create notification directly
    n = NotificationModel(
        id=str(uuid.uuid4()), user_id=user_id, type="email",
        title="Test", message="Hello", channel="email", status="pending",
    )
    db_session.add(n)
    await db_session.commit()

    r = await client.patch(f"/api/v1/notifications/{n.id}/read",
                           headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_notifications_no_auth(client: AsyncClient):
    r = await client.get("/api/v1/notifications")
    assert r.status_code in [401, 403]


@pytest.mark.asyncio
async def test_email_provider_logs_only_without_key():
    """Email provider should log but not crash when no API key set."""
    from modules.notifications.infrastructure.providers import EmailNotificationProvider
    provider = EmailNotificationProvider(api_key="")
    from modules.notifications.domain.entities import Notification
    n = Notification(title="Test", message="Msg")
    # Should not raise
    await provider.send(n)


@pytest.mark.asyncio
async def test_discord_provider_skips_without_url():
    from modules.notifications.infrastructure.providers import DiscordNotificationProvider
    provider = DiscordNotificationProvider(webhook_url="")
    from modules.notifications.domain.entities import Notification
    n = Notification(title="Test", message="Msg")
    await provider.send(n)  # Should log skip, not crash


@pytest.mark.asyncio
async def test_telegram_provider_skips_without_token():
    from modules.notifications.infrastructure.providers import TelegramNotificationProvider
    provider = TelegramNotificationProvider(bot_token="", chat_id="")
    from modules.notifications.domain.entities import Notification
    n = Notification(title="Test", message="Msg")
    await provider.send(n)  # Should log skip, not crash
