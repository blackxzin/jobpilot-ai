"""Jobs module tests — local search and manual job creation."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str) -> str:
    reg = await client.post("/api/v1/auth/register", json={"email": email, "password": "password1234"})
    assert reg.status_code == 200
    return reg.json()["token"]


@pytest.mark.asyncio
async def test_create_manual_job(client: AsyncClient):
    token = await _register(client, "jobowner@example.com")

    response = await client.post(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Dev Backend Python", "company_name": "Nubank", "location": "São Paulo", "location_type": "hybrid"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Dev Backend Python"
    assert body["company"] == "Nubank"
    assert body["source"] == "manual"


@pytest.mark.asyncio
async def test_create_manual_job_requires_auth(client: AsyncClient):
    response = await client.post("/api/v1/jobs", json={"title": "Vaga sem login", "company_name": "Acme"})
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_manual_job_rejects_missing_fields(client: AsyncClient):
    token = await _register(client, "jobowner2@example.com")

    response = await client.post(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "", "company_name": ""},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_manual_job_appears_in_local_search(client: AsyncClient):
    token = await _register(client, "jobowner3@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/api/v1/jobs", headers=headers, json={"title": "Engenheira de Dados", "company_name": "Stone"})

    response = await client.get("/api/v1/jobs", params={"query": "Engenheira"}, headers=headers)

    assert response.status_code == 200
    results = response.json()["results"]
    assert any(j["title"] == "Engenheira de Dados" and j["company"] == "Stone" for j in results)


@pytest.mark.asyncio
async def test_reuses_existing_company_by_name(client: AsyncClient):
    token = await _register(client, "jobowner4@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    first = await client.post("/api/v1/jobs", headers=headers, json={"title": "Vaga 1", "company_name": "Ambev"})
    second = await client.post("/api/v1/jobs", headers=headers, json={"title": "Vaga 2", "company_name": "ambev"})

    assert first.json()["company_id"] == second.json()["company_id"]
