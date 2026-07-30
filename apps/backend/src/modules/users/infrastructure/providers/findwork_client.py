"""Findwork API client — free jobs API (no key for basic search)."""
from __future__ import annotations

from typing import Any
import httpx


class FindworkClient:
    """Client for Findwork.dev Jobs API (free, no key needed)."""

    BASE_URL = "https://findwork.dev/api"

    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "JobPilot-AI/0.1.0 (jobpilot@example.com)",
                "Accept": "application/json",
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def search_jobs(self, query: str = "", page: int = 1) -> list[dict[str, Any]]:
        params = {"search": query, "page": page, "page_size": 20, "sorting": "date"}
        resp = await self._client.get(f"{self.BASE_URL}/jobs/", params=params)
        resp.raise_for_status()
        data = resp.json()
        jobs = data.get("results", [])
        return [{
            "title": j.get("role", j.get("title", "")),
            "company": j.get("company_name", ""),
            "location": j.get("location", "Remote"),
            "description": (j.get("text", j.get("description", "")))[:500],
            "url": j.get("url", j.get("apply_url", "")),
            "source": "findwork",
        } for j in jobs[:20]]
