"""Async plumbing shared by every Celery task.

Celery tasks are synchronous callables, while the entire data layer is async
SQLAlchemy. Each task therefore needs its own event loop and its own engine —
the engine created for the FastAPI process belongs to a different loop and
raises if reused from a worker.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings


def run_async[T](coro_factory: Callable[[], Awaitable[T]]) -> T:
    """Run one coroutine to completion on a fresh event loop."""
    return asyncio.run(coro_factory())


@asynccontextmanager
async def worker_session():
    """Yield a database session bound to a short-lived, task-local engine.

    `pool_size=1` on purpose: a worker process handles one task at a time and
    a larger pool just holds idle connections open against the database.
    """
    engine = create_async_engine(settings.DATABASE_URL, pool_size=1, max_overflow=0, pool_pre_ping=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    finally:
        await engine.dispose()
