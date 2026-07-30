"""Jooble API client — free job search aggregator (no key needed)."""
from __future__ import annotations

from typing import Any
import httpx


class JoobleClient:
    """Client for Jooble Jobs API (free, no key for basic search)."""

    BASE_URL = "https://br.jooble.org/api"

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30.0, headers={"User-Agent": "JobPilot-AI/0.1.0"})

    async def close(self) -> None:
        await self._client.aclose()

    async def search_jobs(self, query: str = "", location: str = "", page: int = 1) -> list[dict[str, Any]]:
        params = {"search": query, "location": location or "Brasil", "page": page}
        resp = await self._client.get(f"{self.BASE_URL}/jobs", params=params)
        resp.raise_for_status()
        data = resp.json()
        jobs = data.get("jobs", []) if isinstance(data, dict) else data
        return [{
            "title": j.get("title", ""),
            "company": j.get("company", ""),
            "location": j.get("location", ""),
            "description": (j.get("snippet") or j.get("description", ""))[:500],
            "url": j.get("url", j.get("link", "")),
            "source": "jooble",
        } for j in (jobs if isinstance(jobs, list) else [])]
