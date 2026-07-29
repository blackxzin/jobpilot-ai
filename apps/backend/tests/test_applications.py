"""Application module tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_application(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json={"email": "app@example.com", "password": "password1234"})
    assert reg.status_code == 200
    token = reg.json()["token"]

    response = await client.post("/api/v1/applications", headers={"Authorization": f"Bearer {token}"},
        json={"job_id": "00000000-0000-0000-0000-000000000000", "resume_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code in [200, 404, 422]


@pytest.mark.asyncio
async def test_list_applications(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "listapp@example.com", "password": "password1234"},
    )
    token = reg.json()["token"]

    response = await client.get(
        "/api/v1/applications/list",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert "results" in response.json()
