"""Regression tests for bugs found during the audit.

Each test here pins down a defect that used to be reachable from the UI.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError, ValidationError
from core.models import ApplicationModel, CompanyModel, JobModel, ResumeModel


async def _register(client: AsyncClient, email: str) -> str:
    r = await client.post("/api/v1/auth/register", json={"email": email, "password": "password1234"})
    assert r.status_code == 200
    return r.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Async lazy-loading ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_load_job_eager_loads_company(db_session: AsyncSession):
    """Reading job.company used to raise MissingGreenlet under async SQLAlchemy."""
    from modules.ai.api.routes import _job_to_prompt_dict, _load_job

    company = CompanyModel(id=str(uuid.uuid4()), name="ACME Corp")
    job = JobModel(id=str(uuid.uuid4()), title="Backend Dev", company_id=company.id)
    db_session.add_all([company, job])
    await db_session.commit()
    db_session.expunge_all()

    loaded = await _load_job(db_session, job.id)
    assert loaded is not None
    assert _job_to_prompt_dict(loaded)["company"] == "ACME Corp"


@pytest.mark.asyncio
async def test_load_job_raises_for_unknown_id(db_session: AsyncSession):
    """A missing job must 404, not silently score against an empty posting."""
    from modules.ai.api.routes import _load_job

    with pytest.raises(NotFoundError):
        await _load_job(db_session, str(uuid.uuid4()))


@pytest.mark.asyncio
async def test_load_job_rejects_malformed_id(db_session: AsyncSession):
    """A malformed id is a 422 from validation, never a driver-level 500."""
    from modules.ai.api.routes import _load_job

    with pytest.raises(ValidationError):
        await _load_job(db_session, "not-a-uuid")


# ── Ownership (IDOR) ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cannot_update_another_users_application(client: AsyncClient, db_session: AsyncSession):
    owner_token = await _register(client, "owner-app@test.com")
    owner_id = (await client.get("/api/v1/auth/me", headers=_auth(owner_token))).json()["id"]
    attacker_token = await _register(client, "attacker-app@test.com")

    application = ApplicationModel(
        id=str(uuid.uuid4()),
        job_id=str(uuid.uuid4()),
        resume_id=str(uuid.uuid4()),
        user_id=owner_id,
        status="applied",
    )
    db_session.add(application)
    await db_session.commit()

    r = await client.patch(
        f"/api/v1/applications/{application.id}/status",
        headers=_auth(attacker_token),
        json={"status": "rejected"},
    )
    assert r.status_code == 404

    ok = await client.patch(
        f"/api/v1/applications/{application.id}/status",
        headers=_auth(owner_token),
        json={"status": "offer"},
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "offer"


@pytest.mark.asyncio
async def test_cannot_read_another_users_resume(client: AsyncClient, db_session: AsyncSession):
    owner_token = await _register(client, "owner-resume@test.com")
    owner_id = (await client.get("/api/v1/auth/me", headers=_auth(owner_token))).json()["id"]
    attacker_token = await _register(client, "attacker-resume@test.com")

    resume = ResumeModel(id=str(uuid.uuid4()), user_id=owner_id, title="Private CV", content_text="secret")
    db_session.add(resume)
    await db_session.commit()

    assert (await client.get(f"/api/v1/resumes/{resume.id}", headers=_auth(attacker_token))).status_code == 404
    assert (await client.get(f"/api/v1/resumes/{resume.id}", headers=_auth(owner_token))).status_code == 200


# ── Input validation (used to be 500s) ──────────────────────────────────────

@pytest.mark.asyncio
async def test_invalid_uuid_returns_422(client: AsyncClient):
    token = await _register(client, "baduuid@test.com")
    r = await client.post(
        "/api/v1/applications",
        headers=_auth(token),
        json={"job_id": "not-a-uuid", "resume_id": "not-a-uuid"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_invalid_status_returns_422(client: AsyncClient):
    token = await _register(client, "badstatus@test.com")
    r = await client.patch(
        f"/api/v1/applications/{uuid.uuid4()}/status",
        headers=_auth(token),
        json={"status": "definitely-not-a-status"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_invalid_notification_id_returns_422(client: AsyncClient):
    token = await _register(client, "badnotif@test.com")
    r = await client.patch("/api/v1/notifications/not-a-uuid/read", headers=_auth(token))
    assert r.status_code == 422


# ── Calendar: errors must use HTTP status codes ─────────────────────────────

@pytest.mark.asyncio
async def test_calendar_crud_and_missing_event_returns_404(client: AsyncClient):
    token = await _register(client, "cal@test.com")

    created = await client.post(
        "/api/v1/calendar",
        headers=_auth(token),
        json={"title": "Entrevista", "event_type": "interview", "date": "2026-09-01T10:00:00Z"},
    )
    assert created.status_code == 200
    event_id = created.json()["id"]

    listed = await client.get("/api/v1/calendar", headers=_auth(token))
    assert any(e["id"] == event_id for e in listed.json()["events"])

    assert (await client.delete(f"/api/v1/calendar/{uuid.uuid4()}", headers=_auth(token))).status_code == 404
    assert (await client.delete(f"/api/v1/calendar/{event_id}", headers=_auth(token))).status_code == 200


@pytest.mark.asyncio
async def test_calendar_rejects_malformed_date(client: AsyncClient):
    token = await _register(client, "calbad@test.com")
    r = await client.post(
        "/api/v1/calendar",
        headers=_auth(token),
        json={"title": "Entrevista", "date": "31/12/2026"},
    )
    assert r.status_code == 422


# ── Password hashing ────────────────────────────────────────────────────────

def test_password_hash_is_salted_and_verifiable():
    from core.security import hash_password, needs_rehash, verify_password

    first, second = hash_password("password1234"), hash_password("password1234")
    assert first != second, "each hash must use a fresh salt"
    assert verify_password("password1234", first)
    assert not verify_password("wrong-password", first)
    assert not needs_rehash(first)


def test_legacy_sha256_hash_still_verifies_but_needs_rehash():
    import hashlib

    from core.security import needs_rehash, verify_password

    legacy = hashlib.sha256(b"password1234").hexdigest()
    assert verify_password("password1234", legacy)
    assert needs_rehash(legacy)


@pytest.mark.asyncio
async def test_login_upgrades_legacy_password_hash(client: AsyncClient, db_session: AsyncSession):
    import hashlib

    from sqlalchemy import select

    from core.models import UserModel

    await _register(client, "legacy@test.com")
    result = await db_session.execute(select(UserModel).where(UserModel.email == "legacy@test.com"))
    user = result.scalar_one()
    user.hashed_password = hashlib.sha256(b"password1234").hexdigest()
    await db_session.commit()

    r = await client.post("/api/v1/auth/login", json={"email": "legacy@test.com", "password": "password1234"})
    assert r.status_code == 200

    await db_session.refresh(user)
    assert user.hashed_password.startswith("pbkdf2_sha256$")


def test_local_embedding_is_finite_and_normalized():
    """Embeddings used to reinterpret hash bytes as float32, yielding inf/NaN."""
    import math

    from modules.search.infrastructure import EmbeddingService, cosine_similarity

    vector = EmbeddingService().local_embed("Python developer")
    assert all(math.isfinite(v) for v in vector)
    assert cosine_similarity(vector, vector) == pytest.approx(1.0, abs=1e-9)

# ── Resume upload ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_rejects_non_pdf_content(client: AsyncClient):
    """Extension checks alone let a renamed archive reach the PDF parser."""
    token = await _register(client, "badpdf@test.com")
    r = await client.post(
        "/api/v1/resumes/upload",
        headers=_auth(token),
        data={"title": "CV"},
        files={"file": ("cv.pdf", b"PK\x03\x04 this is a zip", "application/pdf")},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_upload_rejects_pdf_without_extractable_text(client: AsyncClient):
    """A scanned CV analyses as an empty document; say so instead of storing it."""
    token = await _register(client, "scanned@test.com")
    r = await client.post(
        "/api/v1/resumes/upload",
        headers=_auth(token),
        data={"title": "CV"},
        files={"file": ("cv.pdf", b"%PDF-1.4 no text layer here", "application/pdf")},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_upload_response_matches_list_response_shape(
    client: AsyncClient, pdf_bytes: bytes
):
    """Upload used to return a different field set from list and get."""
    token = await _register(client, "shape@test.com")
    uploaded = await client.post(
        "/api/v1/resumes/upload",
        headers=_auth(token),
        data={"title": "CV"},
        files={"file": ("cv.pdf", pdf_bytes, "application/pdf")},
    )
    assert uploaded.status_code == 200
    listed = (await client.get("/api/v1/resumes/list", headers=_auth(token))).json()["results"][0]
    assert set(uploaded.json()) == set(listed)


# ── Rate limiting ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_is_rate_limited(client: AsyncClient):
    """Unlimited login attempts make offline password guessing free."""
    from core.config import settings
    from core.rate_limit import reset_local_state

    await _register(client, "bruteforce@test.com")
    settings.RATE_LIMIT_ENABLED = True
    reset_local_state()
    try:
        statuses = [
            (
                await client.post(
                    "/api/v1/auth/login",
                    json={"email": "bruteforce@test.com", "password": "wrong-password"},
                )
            ).status_code
            for _ in range(settings.RATE_LIMIT_LOGIN_ATTEMPTS + 2)
        ]
    finally:
        settings.RATE_LIMIT_ENABLED = False
        reset_local_state()

    assert 429 in statuses, "login accepted unlimited attempts"
