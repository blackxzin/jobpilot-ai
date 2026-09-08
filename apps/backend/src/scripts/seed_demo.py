"""CLI to seed (or reset) the demo account.

Usage:
    PYTHONPATH=src python -m scripts.seed_demo
    PYTHONPATH=src python -m scripts.seed_demo --reset

`--reset` removes the demo account *and* the jobs it created. Jobs are global
rows rather than user-owned, so deleting only the user left them behind and
each reseed stacked another copy of the catalogue.
"""
from __future__ import annotations

import argparse
import asyncio

from core.config import settings
from core.database import dispose_db
from core.demo import purge_demo_data, seed_demo_data


async def _main(reset: bool) -> None:
    try:
        if reset:
            removed = await purge_demo_data()
            print(f"Removed the demo account and {removed} demo jobs")

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
