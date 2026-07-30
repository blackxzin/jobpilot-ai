"""Indeed job search client — uses Indeed RSS feed (free, no API key)."""
from __future__ import annotations

from typing import Any
import httpx
from xml.etree import ElementTree


class IndeedClient:
    """Client for Indeed job search via public RSS feed (br.indeed.com)."""

    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "JobPilot-AI/0.1.0"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def search_jobs(self, query: str = "", location: str = "", page: int = 1) -> list[dict[str, Any]]:
        """Search jobs via Indeed RSS feed."""
        params = {"q": query, "start": (page - 1) * 10}
        if location:
            params["l"] = location

        url = "https://br.indeed.com/rss"
        response = await self._client.get(url, params=params)
        response.raise_for_status()

        jobs = []
        try:
            root = ElementTree.fromstring(response.content)
            ns = {"": "http://purl.org/rss/1.0/", "dc": "http://purl.org/dc/elements/1.1/"}
            for item in root.findall(".//item", ns):
                title_el = item.find("title", ns)
                desc_el = item.find("description", ns)
                link_el = item.find("link", ns)
                company_el = item.find("dc:creator", ns)

                title = title_el.text.strip() if title_el is not None else ""
                desc = desc_el.text.strip() if desc_el is not None else ""
                link = link_el.text.strip() if link_el is not None else ""
                company = company_el.text.strip() if company_el is not None else ""

                jobs.append({
                    "title": title,
                    "company": company,
                    "description": desc[:500],
                    "url": link,
                    "source": "indeed",
                    "location": location or "Brasil",
                })
        except Exception:
            pass

        return jobs[:20]
