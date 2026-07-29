"""Gupy API client for job search."""
from __future__ import annotations

from typing import Any

import httpx

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


class GupyClient:
    """Client for the Gupy jobs API.

    Gupy is a Brazilian ATS/job board. Their Public API
    allows searching for published jobs.
    """

    BASE_URL = "https://public.gupy.io/api/v4"

    def __init__(self):
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=30.0,
            headers={"User-Agent": "JobPilot-AI/0.1.0"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def search_jobs(
        self,
        query: str = "",
        location: str = "",
        remote: bool = False,
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        """Search for jobs on Gupy.

        Args:
            query: Search term (job title, skills, etc.)
            location: City or state filter
            remote: Filter for remote-only jobs
            page: Page number
            per_page: Results per page (max 100)

        Returns:
            API response with total, page, and jobs list
        """
        params: dict[str, Any] = {
            "q": query,
            "page": page,
            "perPage": per_page,
        }
        if location:
            params["location"] = location
        if remote:
            params["remote"] = "true"

        logger.info("gupy_search", query=query, remote=remote, page=page)
        response = await self._client.get("/jobs", params=params)
        response.raise_for_status()
        return response.json()

    async def get_job(self, job_id: str) -> dict[str, Any]:
        """Get a specific job by ID."""
        response = await self._client.get(f"/jobs/{job_id}")
        response.raise_for_status()
        return response.json()

    async def get_job_company(self, company_slug: str) -> dict[str, Any]:
        """Get company info by slug."""
        response = await self._client.get(f"/companies/{company_slug}")
        response.raise_for_status()
        return response.json()
