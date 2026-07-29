"""GeekHunter API client — busca de vagas gratuita."""
from __future__ import annotations

from typing import Any
import httpx


class GeekHunterClient:
    """Client for GeekHunter Jobs API (free, no key needed)."""

    BASE_URL = "https://portal.api.geekhunter.com.br"

    def __init__(self):
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=30.0,
            headers={"User-Agent": "JobPilot-AI/0.1.0"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def search_jobs(self, query: str = "", page: int = 1) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"page": page, "limit": 20}
        if query:
            params["search"] = query
        response = await self._client.get("/vagas", params=params)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else data.get("vagas", data.get("jobs", []))

    async def get_job(self, job_id: str) -> dict[str, Any]:
        response = await self._client.get(f"/vaga/{job_id}")
        response.raise_for_status()
        return response.json()
