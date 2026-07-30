"""LinkedIn Jobs client — uses public LinkedIn job search."""
from __future__ import annotations

from typing import Any
import httpx
import re


class LinkedInJobsClient:
    """Client for LinkedIn Jobs search (public, no OAuth required)."""

    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "pt-BR,pt;q=0.9",
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def search_jobs(self, query: str = "", location: str = "", page: int = 1) -> list[dict[str, Any]]:
        """Search jobs on LinkedIn Jobs (public)."""
        params: dict[str, Any] = {
            "keywords": query,
            "location": location or "Brazil",
            "start": (page - 1) * 10,
        }

        response = await self._client.get(
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search",
            params=params,
        )
        response.raise_for_status()

        jobs = []
        html = response.text
        # Extract job cards
        cards = re.findall(
            r'<li[^>]*class="[^"]*job-card[^"]*"[^>]*>(.*?)</li>',
            html,
            re.DOTALL,
        )

        for card in cards[:20]:
            title_m = re.search(r'<h3[^>]*>(.*?)</h3>', card, re.DOTALL)
            company_m = re.search(r'class="[^"]*company-name[^"]*"[^>]*>(.*?)<', card, re.DOTALL)
            loc_m = re.search(r'class="[^"]*location[^"]*"[^>]*>(.*?)<', card, re.DOTALL)
            link_m = re.search(r'href="([^"]*)"', card)

            title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip() if title_m else ""
            company = re.sub(r'<[^>]+>', '', company_m.group(1)).strip() if company_m else ""
            loc = re.sub(r'<[^>]+>', '', loc_m.group(1)).strip() if loc_m else ""
            link = f"https://www.linkedin.com{link_m.group(1)}" if link_m else ""

            if title:
                jobs.append({
                    "title": title,
                    "company": company,
                    "location": loc,
                    "url": link,
                    "source": "linkedin",
                })

        return jobs

    async def get_job_detail(self, job_id: str) -> dict[str, Any]:
        """Get detailed info for a specific job (public page)."""
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
        response = await self._client.get(url)
        response.raise_for_status()
        return {"detail_raw": response.text[:2000]}
