"""Jobicy API client — free remote jobs API."""
from __future__ import annotations

from typing import Any
import httpx


class JobicyClient:
    """Client for Jobicy Jobs API (100% free, no key)."""

    BASE_URL = "https://jobicy.com/api/v2"

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30.0, headers={"User-Agent": "JobPilot-AI/0.1.0"})

    async def close(self) -> None:
        await self._client.aclose()

    async def search_jobs(self, query: str = "", page: int = 1) -> list[dict[str, Any]]:
        resp = await self._client.get(f"{self.BASE_URL}/remote-jobs")
        resp.raise_for_status()
        data = resp.json()
        jobs = data.get("jobs", [])
        if query and jobs:
            q = query.lower()
            jobs = [j for j in jobs if q in (j.get("jobTitle", "") + j.get("companyName", "") + " ".join(j.get("jobIndustry", []))).lower()]
        return [{
            "title": j.get("jobTitle", ""),
            "company": j.get("companyName", ""),
            "location": j.get("jobGeo", "Remote"),
            "description": (j.get("jobExcerpt") or j.get("jobDescription", ""))[:500],
            "url": j.get("url", ""),
            "source": "jobicy",
        } for j in jobs[:20]]
