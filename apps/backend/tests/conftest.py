"""Pytest configuration for JobPilot AI backend tests."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings
from core.database import Base, get_db
from core.rate_limit import reset_local_state
from main import create_app

# Use SQLite for tests (fast, no external deps)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(autouse=True)
def hermetic_llm_settings():
    """Keep ambient credentials out of the test run.

    `OPENAI_API_KEY` is commonly exported in a developer's shell for unrelated
    tools. pydantic-settings picks it up, so the suite silently started making
    real, billable calls to a hosted provider — and failed for reasons that had
    nothing to do with the code under test. Tests exercise the offline
    analyzer, which is deterministic and free.
    """
    saved = {
        name: getattr(settings, name)
        for name in (
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY",
            "OPENROUTER_API_KEY",
            "EMBEDDING_API_KEY",
            "EMAIL_API_KEY",
        )
    }
    for name in saved:
        setattr(settings, name, "")
    yield
    for name, value in saved.items():
        setattr(settings, name, value)


@pytest.fixture(autouse=True)
def isolate_rate_limiter():
    """Keep the shared rate-limit counters out of unrelated tests.

    Every test registers a user from the same client address, so the real
    limit would reject the suite after a handful of tests. Tests that assert
    the limit re-enable it explicitly.
    """
    settings.RATE_LIMIT_ENABLED = False
    reset_local_state()
    yield
    settings.RATE_LIMIT_ENABLED = True
    reset_local_state()


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def build_pdf(text: str = "Python developer with FastAPI and PostgreSQL experience") -> bytes:
    """Build a minimal single-page PDF whose text pypdf can actually extract.

    Tests used a `b"%PDF-1.4 fake"` string, which has the right magic bytes but
    no text layer — indistinguishable from a scanned CV, which the upload now
    rejects on purpose.
    """
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode()

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode() + b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n".encode()
        + b"%%EOF\n"
    )
    return bytes(out)


@pytest.fixture
def pdf_bytes() -> bytes:
    """A small, genuinely parseable PDF for upload tests."""
    return build_pdf()
