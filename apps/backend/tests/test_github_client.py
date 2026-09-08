"""Tests for the GitHub client.

HTTP is stubbed with httpx's MockTransport: these assert the request the client
builds and the shape it returns, without depending on github.com being
reachable or on the runner's rate limit.
"""
from __future__ import annotations

import httpx
import pytest

from modules.users.infrastructure.providers.github_client import GitHubClient

USER_PAYLOAD = {
    "login": "octocat",
    "name": "Pessoa Exemplo",
    "bio": "Backend engineer",
    "location": "São Paulo",
    "blog": "https://exemplo.dev",
    "twitter_username": "octo",
    "public_repos": 12,
    "followers": 340,
    "avatar_url": "https://avatars.example/octocat",
    "html_url": "https://github.com/octocat",
}

REPOS_PAYLOAD = [
    {
        "name": "servico-pagamentos",
        "description": "API de pagamentos",
        "language": "Python",
        "stargazers_count": 42,
        "forks_count": 3,
        "topics": ["fastapi", "postgres"],
        "html_url": "https://github.com/octocat/servico-pagamentos",
    },
    {"name": "cli-tool", "language": "Go", "topics": ["cli"]},
    {"name": "sem-linguagem", "language": None, "topics": []},
]


def _client(handler) -> GitHubClient:
    client = GitHubClient()
    client._client = httpx.AsyncClient(
        base_url=GitHubClient.BASE_URL, transport=httpx.MockTransport(handler)
    )
    return client


@pytest.mark.asyncio
async def test_get_user_maps_the_public_profile():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/users/octocat"
        return httpx.Response(200, json=USER_PAYLOAD)

    client = _client(handler)
    try:
        profile = await client.get_user("octocat")
    finally:
        await client.close()

    assert profile["username"] == "octocat"
    assert profile["name"] == "Pessoa Exemplo"
    assert profile["followers"] == 340


@pytest.mark.asyncio
async def test_repositories_are_requested_for_the_named_user():
    """The old code hit /user/repos — the token owner's repos, not the one asked for."""
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["params"] = dict(request.url.params)
        return httpx.Response(200, json=REPOS_PAYLOAD)

    client = _client(handler)
    try:
        repos = await client.get_repositories("octocat", limit=5)
    finally:
        await client.close()

    assert seen["path"] == "/users/octocat/repos"
    assert seen["params"]["per_page"] == "5"
    assert [repo["name"] for repo in repos] == [
        "servico-pagamentos",
        "cli-tool",
        "sem-linguagem",
    ]
    assert repos[0]["topics"] == ["fastapi", "postgres"]


@pytest.mark.asyncio
async def test_skills_merge_languages_and_topics_without_blanks():
    client = _client(lambda _request: httpx.Response(200, json=REPOS_PAYLOAD))
    try:
        skills = await client.get_skills("octocat")
    finally:
        await client.close()

    assert skills == sorted(["Python", "Go", "fastapi", "postgres", "cli"])
    assert None not in skills


@pytest.mark.asyncio
async def test_an_unknown_user_raises():
    client = _client(lambda _request: httpx.Response(404, json={"message": "Not Found"}))
    try:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_user("does-not-exist")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_languages_and_readme_target_the_repository():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/languages"):
            return httpx.Response(200, json={"Python": 12000, "Go": 400})
        return httpx.Response(200, text="<h1>Leia-me</h1>")

    client = _client(handler)
    try:
        assert await client.get_languages("octocat", "cli-tool") == {"Python": 12000, "Go": 400}
        assert "Leia-me" in await client.get_readme("octocat", "cli-tool")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_social_links_omit_fields_the_profile_left_empty():
    payload = {**USER_PAYLOAD, "blog": "", "twitter_username": ""}
    client = _client(lambda _request: httpx.Response(200, json=payload))
    try:
        links = await client.get_user_links("octocat")
    finally:
        await client.close()

    assert links == {"github": "https://github.com/octocat"}


def test_a_token_is_sent_as_a_bearer_credential(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_example")
    client = GitHubClient()
    assert client._client.headers["Authorization"] == "Bearer ghp_example"


def test_no_authorization_header_without_a_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert "Authorization" not in GitHubClient()._client.headers
