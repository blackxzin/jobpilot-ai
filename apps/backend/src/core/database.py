"""
JobPilot AI — Database Layer

Async SQLAlchemy engine, session factory, and base metadata.
Uses asyncpg driver for PostgreSQL.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy.orm import DeclarativeBase

from core.config import settings

engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


def get_engine() -> AsyncEngine:
    """Create or return the global async engine."""
    global engine
    if engine is None:
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_size=20,
            max_overflow=10,
            pool_recycle=3600,
            pool_pre_ping=True,
        )
    return engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create or return the async session factory."""
    global async_session_factory
    if async_session_factory is None:
        _engine = get_engine()
        async_session_factory = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return async_session_factory


async def get_db() -> AsyncSession:
    """Dependency for FastAPI that yields a DB session per request."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables. For development only."""
    _engine = get_engine()
    async with _engine.begin() as conn:
        # In production, use Alembic migrations instead
        await conn.run_sync(Base.metadata.create_all)


async def dispose_db() -> None:
    """Dispose of the engine."""
    global engine, async_session_factory
    if engine is not None:
        await engine.dispose()
    engine = None
    async_session_factory = None
