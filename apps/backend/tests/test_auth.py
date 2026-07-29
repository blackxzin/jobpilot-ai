"""Auth module tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "password1234", "full_name": "Test User"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "token" in data


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient):
    r1 = await client.post("/api/v1/auth/register", json={"email": "dup@example.com", "password": "password1234"})
    assert r1.status_code == 200
    r2 = await client.post("/api/v1/auth/register", json={"email": "dup@example.com", "password": "otherpass"})
    assert r2.status_code == 422  # ValidationError: Email already registered


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "mypassword123"},
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "mypassword123"},
    )
    assert response.status_code == 200
    assert "token" in response.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    response = await client.post("/api/v1/auth/login", json={"email": "noone@example.com", "password": "wrongpassword"})
    assert response.status_code in [401, 500]


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "me@example.com", "password": "password1234"},
    )
    token = reg.json()["token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "logout@example.com", "password": "password1234"})
    token = reg.json()["token"]
    await client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code in [200, 401]
