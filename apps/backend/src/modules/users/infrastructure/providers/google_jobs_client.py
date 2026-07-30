"""Google Jobs scraper — free job search via Google."""
from __future__ import annotations

from typing import Any
import httpx
import re


class GoogleJobsClient:
    """Scrape Google Jobs results (free, no key)."""

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
        search_q = f"{query} {location or 'Brasil'} emprego".strip()
        params = {"q": search_q, "ibp": "htl;jobs", "start": (page - 1) * 10}
        resp = await self._client.get("https://www.google.com/search", params=params)
        resp.raise_for_status()
        html = resp.text
        jobs = []

        # Extract job data from Google Jobs embedded JSON
        for match in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL):
            try:
                import json
                data = json.loads(match.group(1))
                if not isinstance(data, dict):
                    continue
                # Google Jobs uses ItemList or direct JobPosting
                items = data.get("itemListElement", [])
                for item in items:
                    job = item.get("item", item) if isinstance(item, dict) else item
                    if isinstance(job, dict) and job.get("@type") == "JobPosting":
                        jobs.append({
                            "title": job.get("title", ""),
                            "company": (job.get("hiringOrganization") or {}).get("name", ""),
                            "location": job.get("jobLocation", {}).get("address", {}).get("addressLocality", ""),
                            "description": (job.get("description", "") or "")[:500],
                            "url": job.get("directApply", job.get("url", "")),
                            "source": "google_jobs",
                        })
            except (json.JSONDecodeError, AttributeError):
                continue

        return jobs[:20]
