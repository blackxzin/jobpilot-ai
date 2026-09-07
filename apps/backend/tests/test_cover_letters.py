"""Tests for the cover letters module — history, edit, delete, ownership."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import CoverLetterModel


async def _register(client: AsyncClient, email: str) -> tuple[str, str]:
    r = await client.post("/api/v1/auth/register", json={"email": email, "password": "pass12345"})
    data = r.json()
    return data["token"], data["user_id"]


@pytest.mark.asyncio
async def test_list_cover_letters_empty(client: AsyncClient):
    token, _ = await _register(client, "cl-list@test.com")

    r = await client.get("/api/v1/cover-letters", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_and_get_cover_letter(client: AsyncClient, db_session: AsyncSession):
    token, user_id = await _register(client, "cl-get@test.com")

    letter = CoverLetterModel(
        id=str(uuid.uuid4()), user_id=user_id, title="Dev Vaga X",
        content="Prezados, ...", language="pt-BR", tone="professional",
    )
    db_session.add(letter)
    await db_session.commit()

    listed = await client.get("/api/v1/cover-letters", headers={"Authorization": f"Bearer {token}"})
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == letter.id

    got = await client.get(f"/api/v1/cover-letters/{letter.id}", headers={"Authorization": f"Bearer {token}"})
    assert got.status_code == 200
    assert got.json()["content"] == "Prezados, ..."
    assert got.json()["title"] == "Dev Vaga X"


@pytest.mark.asyncio
async def test_update_cover_letter_content(client: AsyncClient, db_session: AsyncSession):
    token, user_id = await _register(client, "cl-update@test.com")

    letter = CoverLetterModel(id=str(uuid.uuid4()), user_id=user_id, content="original")
    db_session.add(letter)
    await db_session.commit()

    r = await client.patch(
        f"/api/v1/cover-letters/{letter.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "edited by hand", "title": "New title"},
    )
    assert r.status_code == 200
    assert r.json()["content"] == "edited by hand"
    assert r.json()["title"] == "New title"


@pytest.mark.asyncio
async def test_delete_cover_letter(client: AsyncClient, db_session: AsyncSession):
    token, user_id = await _register(client, "cl-delete@test.com")

    letter = CoverLetterModel(id=str(uuid.uuid4()), user_id=user_id, content="to delete")
    db_session.add(letter)
    await db_session.commit()

    r = await client.delete(f"/api/v1/cover-letters/{letter.id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 204

    got = await client.get(f"/api/v1/cover-letters/{letter.id}", headers={"Authorization": f"Bearer {token}"})
    assert got.status_code == 404


@pytest.mark.asyncio
async def test_cover_letter_ownership_enforced(client: AsyncClient, db_session: AsyncSession):
    _, owner_id = await _register(client, "cl-owner@test.com")
    other_token, _ = await _register(client, "cl-intruder@test.com")

    letter = CoverLetterModel(id=str(uuid.uuid4()), user_id=owner_id, content="private letter")
    db_session.add(letter)
    await db_session.commit()

    r = await client.get(f"/api/v1/cover-letters/{letter.id}", headers={"Authorization": f"Bearer {other_token}"})
    assert r.status_code == 404

    r = await client.patch(
        f"/api/v1/cover-letters/{letter.id}",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"content": "hijacked"},
    )
    assert r.status_code == 404

    r = await client.delete(f"/api/v1/cover-letters/{letter.id}", headers={"Authorization": f"Bearer {other_token}"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_generate_cover_letter_no_resume_404(client: AsyncClient):
    token, _ = await _register(client, "cl-gen@test.com")

    r = await client.post(
        "/api/v1/cover-letters/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={"resume_id": "00000000-0000-0000-0000-000000000000",
              "job_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert r.status_code == 404
