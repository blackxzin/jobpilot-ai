"""GitHub API client for importing user profile data."""
from __future__ import annotations

import os
from typing import Any

import httpx

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


class GitHubClient:
    """Client for GitHub REST API v3.

    Provides methods to fetch public profile data,
    repositories, and skills for a given username.
    Used for the 'Import from GitHub' feature.
    """

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None):
        self._token = token or os.getenv("GITHUB_TOKEN", "")
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "JobPilot-AI",
            },
            timeout=30.0,
        )
        if self._token:
            self._client.headers["Authorization"] = f"Bearer {self._token}"

    async def close(self) -> None:
        await self._client.aclose()

    async def get_user(self, username: str) -> dict[str, Any]:
        """Get public user profile data."""
        response = await self._client.get(f"/users/{username}")
        response.raise_for_status()
        data = response.json()
        return {
            "username": data.get("login", ""),
            "name": data.get("name", ""),
            "bio": data.get("bio", ""),
            "location": data.get("location", ""),
            "blog": data.get("blog", ""),
            "twitter": data.get("twitter_username", ""),
            "linkedin": data.get("hireable", False),
            "public_repos": data.get("public_repos", 0),
            "followers": data.get("followers", 0),
            "avatar_url": data.get("avatar_url", ""),
            "html_url": data.get("html_url", ""),
        }

    async def get_repositories(
        self, username: str, limit: int = 30, sort: str = "updated"
    ) -> list[dict[str, Any]]:
        """Get user's public repositories with language and activity data."""
        response = await self._client.get(
            "/user/repos",
            params={
                "sort": sort,
                "per_page": limit,
                "type": "owner",
            },
        )
        response.raise_for_status()
        repos = response.json()

        result = []
        for repo in repos:
            result.append(
                {
                    "name": repo.get("name", ""),
                    "description": repo.get("description", ""),
                    "language": repo.get("language"),
                    "stargazers_count": repo.get("stargazers_count", 0),
                    "forks_count": repo.get("forks_count", 0),
                    "updated_at": repo.get("updated_at", ""),
                    "created_at": repo.get("created_at", ""),
                    "html_url": repo.get("html_url", ""),
                    "topics": repo.get("topics", []),
                    "is_private": repo.get("private", False),
                    "primary_language": repo.get("language"),
                }
            )
        return result

    async def get_languages(self, username: str, repo_name: str) -> dict[str, int]:
        """Get language breakdown for a specific repository."""
        response = await self._client.get(f"/repos/{username}/{repo_name}/languages")
        response.raise_for_status()
        return response.json()

    async def get_readme(self, username: str, repo_name: str) -> str:
        """Get README content for a repository."""
        response = await self._client.get(
            f"/repos/{username}/{repo_name}/readme",
            headers={"Accept": "application/vnd.github.v3.html"},
        )
        response.raise_for_status()
        return response.text

    async def get_skills(self, username: str) -> list[str]:
        """Extract a list of programming languages and technologies
        used across all public repos."""
        repos = await self.get_repositories(username, limit=50)
        languages: set[str] = set()

        for repo in repos:
            lang = repo.get("primary_language")
            if lang:
                languages.add(lang)

            # Also extract from repo topics
            topics = repo.get("topics", [])
            for topic in topics:
                languages.add(topic)

        return sorted(languages)

    async def get_user_links(self, username: str) -> dict[str, str]:
        """Get social links from the user's profile."""
        user = await self.get_user(username)
        links: dict[str, str] = {}

        if user.get("blog"):
            links["website"] = user["blog"]
        if user.get("twitter"):
            links["twitter"] = f"https://twitter.com/{user['twitter']}"
        if user.get("html_url"):
            links["github"] = user["html_url"]

        return links
