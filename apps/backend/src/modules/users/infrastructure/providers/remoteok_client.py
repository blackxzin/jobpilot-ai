"""RemoteOK API client — busca de vagas 100% gratuita."""
from __future__ import annotations

from typing import Any
import httpx


class RemoteOKClient:
    """Client for RemoteOK Jobs API (completely free, no key needed)."""

    BASE_URL = "https://remoteok.com/api"

    def __init__(self):
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=30.0,
            headers={"User-Agent": "JobPilot-AI/0.1.0"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def search_jobs(self, query: str = "", page: int = 1) -> list[dict[str, Any]]:
        params = {"page": page}
        if query:
            params["search"] = query
        response = await self._client.get("", params=params)
        response.raise_for_status()
        jobs = response.json()
        # First item is usually meta — skip if dict
        if jobs and isinstance(jobs[0], dict) and "slug" not in jobs[0]:
            jobs = jobs[1:]
        return jobs

    async def get_job(self, slug: str) -> dict[str, Any]:
        response = await self._client.get(f"/{slug}")
        response.raise_for_status()
        data = response.json()
        return data[1] if isinstance(data, list) and len(data) > 1 else data[0] if isinstance(data, list) else data
