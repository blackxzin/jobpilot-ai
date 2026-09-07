"""Tests for LLM provider configuration.

These routes hold the user's API keys, so the important behaviours are that
the key is encrypted at rest, never echoed back, and that an unknown provider
is rejected instead of stored.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import LLMProviderConfigModel

SECRET = "sk-super-secret-value"


async def _register(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "password1234"}
    )
    return response.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_provider_catalogue_is_public_shape(client: AsyncClient):
    token = await _register(client, "providers@test.com")
    response = await client.get("/api/v1/settings/providers", headers=_auth(token))

    assert response.status_code == 200
    providers = response.json()["providers"]
    assert {p["id"] for p in providers} >= {"openai", "anthropic", "ollama", "nvidia_nim"}


@pytest.mark.asyncio
async def test_key_is_encrypted_at_rest_and_never_returned(
    client: AsyncClient, db_session: AsyncSession
):
    token = await _register(client, "encrypt@test.com")

    saved = await client.post(
        "/api/v1/settings/llm",
        headers=_auth(token),
        json={"provider_name": "openai", "api_key": SECRET, "model": "gpt-4o"},
    )
    assert saved.status_code == 200

    stored = (await db_session.execute(select(LLMProviderConfigModel))).scalar_one()
    assert SECRET not in stored.api_key_encrypted

    from core.security import decrypt_api_key

    assert decrypt_api_key(stored.api_key_encrypted) == SECRET

    listed = await client.get("/api/v1/settings/llm", headers=_auth(token))
    body = listed.json()["configs"][0]
    assert body["has_key"] is True
    assert SECRET not in listed.text


@pytest.mark.asyncio
async def test_unknown_provider_is_rejected(client: AsyncClient):
    token = await _register(client, "unknown@test.com")
    response = await client.post(
        "/api/v1/settings/llm",
        headers=_auth(token),
        json={"provider_name": "skynet", "api_key": "x"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_updating_without_a_key_keeps_the_existing_one(
    client: AsyncClient, db_session: AsyncSession
):
    """The UI sends an empty field to mean "leave the key alone"."""
    token = await _register(client, "keepkey@test.com")
    await client.post(
        "/api/v1/settings/llm",
        headers=_auth(token),
        json={"provider_name": "openai", "api_key": SECRET},
    )
    await client.post(
        "/api/v1/settings/llm",
        headers=_auth(token),
        json={"provider_name": "openai", "api_key": "", "model": "gpt-4o-mini"},
    )

    from core.security import decrypt_api_key

    stored = (await db_session.execute(select(LLMProviderConfigModel))).scalar_one()
    assert decrypt_api_key(stored.api_key_encrypted) == SECRET
    assert stored.model == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_configuration_is_private_to_its_owner(client: AsyncClient):
    owner = await _register(client, "owner-cfg@test.com")
    await client.post(
        "/api/v1/settings/llm",
        headers=_auth(owner),
        json={"provider_name": "openai", "api_key": SECRET},
    )

    other = await _register(client, "other-cfg@test.com")
    response = await client.get("/api/v1/settings/llm", headers=_auth(other))
    assert response.json()["configs"] == []


@pytest.mark.asyncio
async def test_configuration_requires_a_session(client: AsyncClient):
    assert (await client.get("/api/v1/settings/llm")).status_code == 401
