"""End-to-end AI routes against the offline analyzer, plus malformed-id handling."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient, email: str, pdf: bytes) -> tuple[dict, str, str]:
    reg = await client.post("/api/v1/auth/register", json={"email": email, "password": "pass12345"})
    headers = {"Authorization": f"Bearer {reg.json()['token']}"}

    resume = await client.post(
        "/api/v1/resumes/upload", headers=headers,
        data={"title": "CV"}, files={"file": ("cv.pdf", pdf, "application/pdf")},
    )
    job = await client.post(
        "/api/v1/jobs", headers=headers,
        json={"title": "Backend Python", "company_name": "Acme",
              "description": "Python, FastAPI and PostgreSQL. Docker is a plus."},
    )
    return headers, resume.json()["id"], job.json()["id"]


@pytest.mark.asyncio
async def test_ai_routes_work_offline_and_letters_are_saved(client: AsyncClient, pdf_bytes: bytes):
    headers, resume_id, job_id = await _setup(client, "ai-flow@test.com", pdf_bytes)
    body = {"resume_id": resume_id, "job_id": job_id}

    match = await client.post("/api/v1/ai/match", headers=headers, json=body)
    assert match.status_code == 200, match.text

    ats = await client.post("/api/v1/ai/ats-score", headers=headers, json=body)
    assert ats.status_code == 200, ats.text

    tailored = await client.post("/api/v1/ai/tailor-resume", headers=headers, json=body)
    assert tailored.status_code == 200 and tailored.json()["tailored_resume"]

    letter = await client.post("/api/v1/ai/cover-letter", headers=headers, json=body)
    assert letter.status_code == 200 and letter.json()["cover_letter"]

    generated = await client.post("/api/v1/cover-letters/generate", headers=headers, json=body)
    assert generated.status_code == 200 and generated.json()["content"]

    history = await client.get("/api/v1/cover-letters", headers=headers)
    assert {letter.json()["id"], generated.json()["id"]} <= {c["id"] for c in history.json()}


@pytest.mark.asyncio
async def test_malformed_ids_are_422_not_500(client: AsyncClient, pdf_bytes: bytes):
    """SQLite tolerates any string as an id; Postgres raises, which was a 500."""
    headers, _, job_id = await _setup(client, "bad-ids@test.com", pdf_bytes)

    responses = [
        await client.get("/api/v1/cover-letters/not-a-uuid", headers=headers),
        await client.patch("/api/v1/cover-letters/not-a-uuid", headers=headers, json={"content": "x"}),
        await client.delete("/api/v1/cover-letters/not-a-uuid", headers=headers),
        await client.post("/api/v1/cover-letters/generate", headers=headers,
                          json={"resume_id": "not-a-uuid", "job_id": job_id}),
        await client.patch("/api/v1/calendar/not-a-uuid", headers=headers, json={"title": "x"}),
        await client.delete("/api/v1/calendar/not-a-uuid", headers=headers),
        await client.patch("/api/v1/applications/not-a-uuid/status", headers=headers,
                           json={"status": "interview"}),
    ]
    assert [r.status_code for r in responses] == [422] * len(responses), [r.text for r in responses]
