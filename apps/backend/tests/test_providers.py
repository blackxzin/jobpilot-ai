"""Tests for the LLM provider adapters.

Each adapter is a thin translation between the provider port and one vendor
SDK. The SDK itself is stubbed: what matters is that the adapter sends the
configured model, forwards the prompt, and reads the response shape correctly
— all things that used to be copy-pasted six times and could drift.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest


class _FakeCompletions:
    def __init__(self, content: str, recorder: dict):
        self._content = content
        self._recorder = recorder

    async def create(self, **kwargs):
        self._recorder.update(kwargs)
        message = SimpleNamespace(content=self._content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _fake_openai_client(content: str, recorder: dict):
    return SimpleNamespace(
        chat=SimpleNamespace(completions=_FakeCompletions(content, recorder)),
        models=SimpleNamespace(list=_always_ok),
    )


async def _always_ok():
    return SimpleNamespace(data=[])


@pytest.mark.asyncio
async def test_openai_adapter_sends_configured_model_and_prompt():
    from modules.ai.infrastructure.llm_providers.openai_provider import OpenAIProvider

    recorder: dict = {}
    provider = OpenAIProvider(api_key="test", model="gpt-4o-mini")
    provider._client = _fake_openai_client("resposta", recorder)

    assert await provider.generate("pergunta") == "resposta"
    assert recorder["model"] == "gpt-4o-mini"
    assert recorder["messages"] == [{"role": "user", "content": "pergunta"}]
    assert provider.provider_name == "openai"


@pytest.mark.asyncio
async def test_adapters_parse_json_through_the_shared_helper():
    """A fenced JSON block is the common wrapping; every adapter must handle it."""
    from modules.ai.infrastructure.llm_providers.openai_provider import OpenAIProvider

    fenced = '```json\n{"compatibility_score": 73, "match_reasons": [], "suggestions": []}\n```'
    provider = OpenAIProvider(api_key="test")
    provider._client = _fake_openai_client(fenced, {})

    result = await provider.compare_job("CV", {"title": "Backend"})
    assert result["compatibility_score"] == 73


@pytest.mark.asyncio
async def test_unparseable_response_reports_a_parse_error():
    from modules.ai.infrastructure.llm_providers.openai_provider import OpenAIProvider

    provider = OpenAIProvider(api_key="test")
    provider._client = _fake_openai_client("desculpe, não consigo", {})

    result = await provider.analyze_resume("CV", "vaga")
    assert "parse_error" in result


@pytest.mark.asyncio
async def test_empty_completion_becomes_an_empty_string():
    from modules.ai.infrastructure.llm_providers.openai_provider import OpenAIProvider

    provider = OpenAIProvider(api_key="test")
    provider._client = _fake_openai_client(None, {})
    assert await provider.generate("oi") == ""


@pytest.mark.asyncio
async def test_health_check_reports_false_when_the_provider_is_down():
    from modules.ai.infrastructure.llm_providers.openai_provider import OpenAIProvider

    async def explode():
        raise RuntimeError("unreachable")

    provider = OpenAIProvider(api_key="test")
    provider._client = SimpleNamespace(models=SimpleNamespace(list=explode))
    assert await provider.health_check() is False


@pytest.mark.asyncio
async def test_openrouter_targets_its_own_endpoint():
    from modules.ai.infrastructure.llm_providers.openrouter_provider import (
        OPENROUTER_BASE_URL,
        OpenRouterProvider,
    )

    provider = OpenRouterProvider(api_key="test")
    assert provider.provider_name == "openrouter"
    assert str(provider._client.base_url).startswith(OPENROUTER_BASE_URL)


@pytest.mark.asyncio
async def test_ollama_posts_to_the_configured_server():
    from modules.ai.infrastructure.llm_providers.ollama_provider import OllamaProvider

    captured: dict = {}

    class _FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"response": "olá"}

    class _FakeHttp:
        async def post(self, url, json):
            captured["url"] = url
            captured["json"] = json
            return _FakeResponse()

    provider = OllamaProvider(base_url="http://ollama:11434/", model="mistral")
    provider._client = _FakeHttp()

    assert await provider.generate("oi") == "olá"
    # The trailing slash must not produce a double slash in the path.
    assert captured["url"] == "http://ollama:11434/api/generate"
    assert captured["json"]["model"] == "mistral"
    assert captured["json"]["stream"] is False
    assert provider.provider_name == "ollama"


def test_every_registered_provider_implements_the_port():
    """The port is what the application depends on; a partial adapter is a 500."""
    from modules.ai.domain.llm_provider import LLMProvider
    from modules.ai.infrastructure.providers.factory import LLMProviderFactory

    required = {
        name
        for name, value in vars(LLMProvider).items()
        if getattr(value, "__isabstractmethod__", False)
    }

    for name in LLMProviderFactory.list_providers():
        if name == "gemini":
            continue  # constructing it configures the vendor SDK globally
        provider = LLMProviderFactory.create(name, api_key="test")
        missing = [method for method in required if not hasattr(provider, method)]
        assert not missing, f"{name} is missing {missing}"
