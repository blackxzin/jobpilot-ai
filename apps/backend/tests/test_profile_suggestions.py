"""Tests for profile positioning.

This endpoint used to ask the model to infer a person's profile from a
LinkedIn URL alone, with no access to the page — a confident, wholly invented
biography. It now works from the user's own resume, and these tests pin that
contract down.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import ResumeModel

RESUME = """Ana Souza — Engenheira de Plataforma
ana.souza@exemplo.com

RESUMO
Engenheira com 7 anos de experiência em infraestrutura e plataformas internas.

EXPERIÊNCIA
Engenheira de Plataforma — Nuvem (2021 - atual)
- Migrei 40 serviços para Kubernetes, reduzindo o tempo de deploy em 65%.

COMPETÊNCIAS
Kubernetes, Terraform, Go, Linux, AWS, observability, cicd, python.
"""


async def _register(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "password1234"}
    )
    assert response.status_code == 200
    return response.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_suggestions_require_a_resume(client: AsyncClient):
    """Without a resume there is nothing to ground the suggestions in."""
    token = await _register(client, "noresume@test.com")
    response = await client.post("/api/v1/ai/linkedin/analyze", headers=_auth(token), json={})

    assert response.status_code == 422
    assert "currículo" in response.json()["detail"]


@pytest.mark.asyncio
async def test_suggestions_are_derived_from_the_resume(
    client: AsyncClient, db_session: AsyncSession
):
    token = await _register(client, "profile@test.com")
    user_id = (await client.get("/api/v1/auth/me", headers=_auth(token))).json()["id"]
    db_session.add(ResumeModel(user_id=user_id, title="CV", content_text=RESUME))
    await db_session.commit()

    response = await client.post(
        "/api/v1/ai/linkedin/analyze",
        headers=_auth(token),
        json={"target_role": "Staff Engineer"},
    )
    assert response.status_code == 200
    body = response.json()

    # Every field must trace back to the resume.
    assert "Staff Engineer" in body["headline"]
    assert "kubernetes" in body["skills"]
    assert "terraform" in body["skills"]
    assert body["experience_years"] == 7
    assert any("Plataforma" in role for role in body["suggested_roles"])


@pytest.mark.asyncio
async def test_suggestions_use_a_specific_resume_when_given(
    client: AsyncClient, db_session: AsyncSession
):
    token = await _register(client, "specific@test.com")
    user_id = (await client.get("/api/v1/auth/me", headers=_auth(token))).json()["id"]
    resume = ResumeModel(user_id=user_id, title="CV", content_text=RESUME)
    db_session.add(resume)
    await db_session.commit()

    response = await client.post(
        "/api/v1/ai/linkedin/analyze",
        headers=_auth(token),
        json={"resume_id": str(resume.id)},
    )
    assert response.status_code == 200
    assert "kubernetes" in response.json()["skills"]


@pytest.mark.asyncio
async def test_cannot_use_another_users_resume(client: AsyncClient, db_session: AsyncSession):
    owner_token = await _register(client, "owner-profile@test.com")
    owner_id = (await client.get("/api/v1/auth/me", headers=_auth(owner_token))).json()["id"]
    resume = ResumeModel(user_id=owner_id, title="CV", content_text=RESUME)
    db_session.add(resume)
    await db_session.commit()

    attacker_token = await _register(client, "attacker-profile@test.com")
    # The attacker has their own resume, so the request is well-formed.
    attacker_id = (await client.get("/api/v1/auth/me", headers=_auth(attacker_token))).json()["id"]
    db_session.add(ResumeModel(user_id=attacker_id, title="Mine", content_text="Dev júnior."))
    await db_session.commit()

    response = await client.post(
        "/api/v1/ai/linkedin/analyze",
        headers=_auth(attacker_token),
        json={"resume_id": str(resume.id)},
    )
    assert response.status_code == 404


# ── Grounding helpers ───────────────────────────────────────────────────────

def test_experience_years_read_from_an_explicit_statement():
    from modules.ai.infrastructure.llm_providers.offline_provider import _infer_experience_years

    assert _infer_experience_years("Profissional com 12 anos de experiência.") == 12
    assert _infer_experience_years("Engineer with 4 years of experience.") == 4


def test_experience_years_fall_back_to_the_span_of_dates():
    from modules.ai.infrastructure.llm_providers.offline_provider import _infer_experience_years

    assert _infer_experience_years("Empresa A (2015 - 2020)\nEmpresa B (2020 - 2023)") == 8


def test_experience_years_are_zero_when_the_resume_says_nothing():
    from modules.ai.infrastructure.llm_providers.offline_provider import _infer_experience_years

    assert _infer_experience_years("Desenvolvedor de software.") == 0


def test_roles_are_only_suggested_when_the_resume_supports_them():
    from modules.ai.infrastructure.llm_providers.offline_provider import _suggest_roles

    assert _suggest_roles(["react", "typescript", "css"]) == ["Desenvolvedor(a) Frontend"]
    assert _suggest_roles([]) == []
    assert "Engenheiro(a) de Machine Learning" not in _suggest_roles(["python", "sql"])


@pytest.mark.asyncio
async def test_offline_suggestions_never_invent_skills():
    from modules.ai.infrastructure.llm_providers.offline_provider import OfflineProvider

    result = await OfflineProvider().suggest_profile("Trabalho com python e docker.")
    assert set(result["skills"]) <= {"python", "docker"}
