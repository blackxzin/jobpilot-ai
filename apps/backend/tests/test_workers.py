"""Tests for the Celery tasks.

These used to be `TODO` stubs that logged a line and returned, while
docker-compose ran two worker services around the clock. Now that they read
and write real rows, they need the same coverage as the API.

Each test swaps `worker_session` for the test session: the real one builds a
PostgreSQL engine from settings, which is not what the suite runs against.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import (
    ApplicationModel,
    CompanyModel,
    JobEmbeddingModel,
    JobMatchModel,
    JobModel,
    JobRequirementModel,
    NotificationModel,
    ResumeModel,
    UserModel,
)

RESUME_TEXT = """Ana Souza — Engenheira Backend
ana.souza@exemplo.com

RESUMO
Engenheira backend com 6 anos de experiência em sistemas distribuídos.

EXPERIÊNCIA
Tech Lead — Nuvem Pagamentos (2023 - atual)
- Reduzi a latência p95 de 820ms para 140ms.
- Absorvi picos de 12x no Black Friday sem degradação.
- Elevei a cobertura de testes de 22% para 84%.

FORMAÇÃO
Bacharelado em Ciência da Computação

COMPETÊNCIAS
Python, FastAPI, Django, PostgreSQL, Redis, Celery, Docker, Kubernetes, AWS, pytest, git.
"""


@pytest.fixture
def patch_worker_session(monkeypatch, db_session: AsyncSession):
    """Point every worker at the test session instead of a new engine."""

    def apply(module) -> None:
        @asynccontextmanager
        async def scope():
            yield db_session
            await db_session.flush()

        monkeypatch.setattr(module, "worker_session", scope)

    return apply


async def _seed_user_and_resume(db_session: AsyncSession) -> tuple[UserModel, ResumeModel]:
    user = UserModel(email="worker@test.com", hashed_password="x", full_name="Worker")
    db_session.add(user)
    await db_session.flush()

    resume = ResumeModel(user_id=user.id, title="CV", content_text=RESUME_TEXT)
    db_session.add(resume)
    await db_session.flush()
    return user, resume


async def _seed_job(db_session: AsyncSession, title: str, skills: list[str]) -> JobModel:
    company = CompanyModel(name=f"{title} Co")
    db_session.add(company)
    await db_session.flush()

    job = JobModel(
        title=title,
        company_id=company.id,
        description=f"Vaga de {title}. Requisitos: {', '.join(skills)}.",
        is_active=True,
    )
    db_session.add(job)
    await db_session.flush()

    for skill in skills:
        db_session.add(JobRequirementModel(job_id=job.id, requirement=skill, category="skill"))
    await db_session.flush()
    return job


# ── ATS scoring ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ats_scoring_persists_score(patch_worker_session, db_session: AsyncSession):
    """`resumes.ats_score` is read by the dashboard but was never written."""
    import workers.ats_scoring as module

    patch_worker_session(module)
    _, resume = await _seed_user_and_resume(db_session)

    result = await module._score(str(resume.id))

    assert result["status"] == "completed"
    assert 0 < result["score"] <= 100
    await db_session.refresh(resume)
    assert resume.ats_score == result["score"]
    assert resume.ats_breakdown["matched_skills"]


@pytest.mark.asyncio
async def test_ats_scoring_reports_missing_resume(patch_worker_session, db_session: AsyncSession):
    import uuid

    import workers.ats_scoring as module

    patch_worker_session(module)
    result = await module._score(str(uuid.uuid4()))
    assert result["status"] == "not_found"


# ── Matching ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_matching_stores_only_relevant_jobs(patch_worker_session, db_session: AsyncSession):
    """The job_matches table existed with a full schema but stayed empty."""
    import workers.matching as module

    patch_worker_session(module)
    _, resume = await _seed_user_and_resume(db_session)
    await _seed_job(db_session, "Backend Python", ["python", "fastapi", "postgresql", "docker"])
    await _seed_job(db_session, "Designer Gráfico", ["photoshop", "illustrator", "branding"])

    result = await module._run_matching(str(resume.id), limit=50)

    assert result["status"] == "completed"
    assert result["scanned"] == 2

    matches = (await db_session.execute(select(JobMatchModel))).scalars().all()
    titles = {
        (await db_session.get(JobModel, match.job_id)).title for match in matches
    }
    assert "Backend Python" in titles
    assert "Designer Gráfico" not in titles, "an unrelated job scored above the threshold"


@pytest.mark.asyncio
async def test_matching_is_idempotent(patch_worker_session, db_session: AsyncSession):
    """Re-running must not duplicate a match the user has already seen."""
    import workers.matching as module

    patch_worker_session(module)
    _, resume = await _seed_user_and_resume(db_session)
    await _seed_job(db_session, "Backend Python", ["python", "fastapi", "postgresql", "docker"])

    first = await module._run_matching(str(resume.id), limit=50)
    second = await module._run_matching(str(resume.id), limit=50)

    assert first["matches"] >= 1
    assert second["matches"] == 0
    total = await db_session.scalar(select(func.count()).select_from(JobMatchModel))
    assert total == first["matches"]


@pytest.mark.asyncio
async def test_matching_reports_missing_resume(patch_worker_session, db_session: AsyncSession):
    import uuid

    import workers.matching as module

    patch_worker_session(module)
    result = await module._run_matching(str(uuid.uuid4()), limit=10)
    assert result["status"] == "not_found"


# ── Notification delivery ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pending_notifications_are_delivered(patch_worker_session, db_session: AsyncSession):
    """Pending rows were written by the API and then never read by anything."""
    import workers.email_notifications as module

    patch_worker_session(module)
    user, _ = await _seed_user_and_resume(db_session)
    db_session.add(
        NotificationModel(
            user_id=user.id,
            channel="email",
            title="Entrevista",
            message="Confirmada",
            status="pending",
        )
    )
    await db_session.flush()

    result = await module._deliver_pending(limit=10)

    # Without EMAIL_API_KEY the provider skips the send without raising, which
    # still counts as handled — the row must not stay pending forever.
    assert result["status"] == "completed"
    assert result["sent"] == 1
    row = (await db_session.execute(select(NotificationModel))).scalar_one()
    assert row.status == "sent"


@pytest.mark.asyncio
async def test_unknown_channel_is_marked_failed(patch_worker_session, db_session: AsyncSession):
    import workers.email_notifications as module

    patch_worker_session(module)
    user, _ = await _seed_user_and_resume(db_session)
    db_session.add(
        NotificationModel(
            user_id=user.id, channel="carrier-pigeon", title="?", message="?", status="pending"
        )
    )
    await db_session.flush()

    result = await module._deliver_pending(limit=10)
    assert result["failed"] == 1
    row = (await db_session.execute(select(NotificationModel))).scalar_one()
    assert row.status == "failed"


@pytest.mark.asyncio
async def test_delivery_is_a_noop_when_nothing_is_pending(
    patch_worker_session, db_session: AsyncSession
):
    import workers.email_notifications as module

    patch_worker_session(module)
    assert await module._deliver_pending(limit=10) == {"status": "completed", "sent": 0, "failed": 0}


# ── Auto apply ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auto_apply_creates_application_and_cover_letter(
    patch_worker_session, db_session: AsyncSession
):
    import workers.auto_apply as module

    patch_worker_session(module)
    user, resume = await _seed_user_and_resume(db_session)
    job = await _seed_job(db_session, "Backend Python", ["python", "fastapi"])

    result = await module._apply(str(user.id), str(job.id), str(resume.id))

    assert result["status"] == "completed"
    application = (await db_session.execute(select(ApplicationModel))).scalar_one()
    assert application.status == "applied"
    assert application.cover_letter


@pytest.mark.asyncio
async def test_auto_apply_does_not_apply_twice(patch_worker_session, db_session: AsyncSession):
    """Applying to the same job twice is embarrassing, not just redundant."""
    import workers.auto_apply as module

    patch_worker_session(module)
    user, resume = await _seed_user_and_resume(db_session)
    job = await _seed_job(db_session, "Backend Python", ["python"])

    await module._apply(str(user.id), str(job.id), str(resume.id))
    second = await module._apply(str(user.id), str(job.id), str(resume.id))

    assert second["status"] == "already_applied"
    assert await db_session.scalar(select(func.count()).select_from(ApplicationModel)) == 1


@pytest.mark.asyncio
async def test_auto_apply_reports_missing_input(patch_worker_session, db_session: AsyncSession):
    import uuid

    import workers.auto_apply as module

    patch_worker_session(module)
    result = await module._apply(str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4()))
    assert result["status"] == "not_found"


# ── Scraping ────────────────────────────────────────────────────────────────

class _FakeBoard:
    """Stands in for a job-board client so tests make no network calls."""

    def __init__(self, postings: list[dict] | None = None, fail: bool = False):
        self._postings = postings or []
        self._fail = fail
        self.closed = False

    async def search_jobs(self, **_kwargs) -> list[dict]:
        if self._fail:
            raise RuntimeError("board unreachable")
        return self._postings

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_scraping_imports_and_indexes_jobs(
    patch_worker_session, monkeypatch, db_session: AsyncSession
):
    import workers.scraping as module

    patch_worker_session(module)
    board = _FakeBoard(
        [
            {
                "id": "remote-1",
                "title": "Backend Engineer",
                "company": "Acme",
                "description": "Python and PostgreSQL",
                "is_remote": True,
                "url": "https://example.com/1",
            }
        ]
    )
    monkeypatch.setattr(module, "_client_for", lambda _source: board)

    result = await module._scrape("remoteok", "python")

    assert result["imported"] == 1
    assert board.closed, "the HTTP client was left open"
    job = (await db_session.execute(select(JobModel))).scalar_one()
    assert job.source == "remoteok"
    # Indexed on ingest, so it is searchable without a separate manual step.
    embedding = (await db_session.execute(select(JobEmbeddingModel))).scalar_one()
    assert embedding.job_id == job.id
    assert len(embedding.embedding) > 0


@pytest.mark.asyncio
async def test_scraping_skips_postings_already_stored(
    patch_worker_session, monkeypatch, db_session: AsyncSession
):
    """The schedule runs every few hours; re-imports must not pile up."""
    import workers.scraping as module

    patch_worker_session(module)
    posting = {"id": "remote-1", "title": "Backend Engineer", "company": "Acme"}
    monkeypatch.setattr(module, "_client_for", lambda _source: _FakeBoard([posting]))

    await module._scrape("remoteok", "python")
    second = await module._scrape("remoteok", "python")

    assert second["imported"] == 0
    assert await db_session.scalar(select(func.count()).select_from(JobModel)) == 1


@pytest.mark.asyncio
async def test_scraping_survives_an_unreachable_board(
    patch_worker_session, monkeypatch, db_session: AsyncSession
):
    import workers.scraping as module

    patch_worker_session(module)
    monkeypatch.setattr(module, "_client_for", lambda _source: _FakeBoard(fail=True))

    result = await module._scrape("remoteok", "python")

    assert result["imported"] == 0
    assert "error" in result
    assert await db_session.scalar(select(func.count()).select_from(JobModel)) == 0


@pytest.mark.asyncio
async def test_scraping_ignores_postings_without_a_title(
    patch_worker_session, monkeypatch, db_session: AsyncSession
):
    import workers.scraping as module

    patch_worker_session(module)
    monkeypatch.setattr(
        module, "_client_for", lambda _source: _FakeBoard([{"id": "x", "company": "Acme"}])
    )

    assert (await module._scrape("remoteok", "python"))["imported"] == 0


def test_unsupported_source_is_rejected():
    from workers.scraping import _client_for

    with pytest.raises(ValueError, match="Unsupported job source"):
        _client_for("monster")


# ── Standalone resume audit ─────────────────────────────────────────────────

def test_audit_rewards_a_well_formed_resume():
    """A standalone ATS score must separate a good CV from a bad one.

    Scoring a resume by overlap with a generic role profile put every CV near
    the floor, because nobody lists every technology in the industry.
    """
    from modules.ai.infrastructure.llm_providers.offline_provider import audit_resume

    strong, _, _ = audit_resume(RESUME_TEXT)
    weak, _, weak_suggestions = audit_resume("Sou dev. Trabalhei numa empresa.")

    assert strong > 70
    assert weak < 30
    assert weak_suggestions, "a weak resume must come with advice"


def test_audit_of_empty_text_scores_zero():
    from modules.ai.infrastructure.llm_providers.offline_provider import audit_resume

    score, strengths, suggestions = audit_resume("")
    assert score == 0
    assert not strengths
    assert suggestions


def test_tokenizer_strips_trailing_punctuation():
    """"git." at the end of a sentence must still match the skill "git".

    Internal punctuation stays: "next.js" and "c++" are real terms.
    """
    from modules.ai.infrastructure.llm_providers.offline_provider import extract_skills, tokenize

    assert "git" in extract_skills("Ferramentas: docker, git.")
    assert "next.js" in tokenize("Trabalho com next.js e react")
