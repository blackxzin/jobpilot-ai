"""CLI to seed (or reset) the demo account.

Usage:
    PYTHONPATH=src python -m scripts.seed_demo
    PYTHONPATH=src python -m scripts.seed_demo --reset

`--reset` deletes the demo user first; every demo row hangs off it by a
cascading foreign key, so removing the user removes the whole dataset.
"""
from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from core.config import settings
from core.database import dispose_db, get_session_factory
from core.demo import seed_demo_data
from core.models import UserModel


async def _delete_demo_user() -> bool:
    session_factory = get_session_factory()
    async with session_factory() as session:
        user = (
            await session.execute(
                select(UserModel).where(UserModel.email == settings.DEMO_EMAIL)
            )
        ).scalar_one_or_none()
        if user is None:
            return False
        await session.delete(user)
        await session.commit()
        return True


async def _main(reset: bool) -> None:
    try:
        if reset and await _delete_demo_user():
            print(f"Removed existing demo account {settings.DEMO_EMAIL}")

        if await seed_demo_data():
            print(f"Demo account ready: {settings.DEMO_EMAIL} / {settings.DEMO_PASSWORD}")
        else:
            print(
                f"Demo account {settings.DEMO_EMAIL} already exists. "
                "Re-run with --reset to rebuild it."
            )
    finally:
        await dispose_db()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the JobPilot demo account.")
    parser.add_argument("--reset", action="store_true", help="delete and rebuild the demo data")
    asyncio.run(_main(parser.parse_args().reset))
