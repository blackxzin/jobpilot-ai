"""Tests for LLMService — the layer between routes and provider adapters.

Its job is to add caching, logging and error translation without any route
knowing which provider is in use.
"""
from __future__ import annotations

import pytest

from core.exceptions import LLMProviderError
from modules.ai.application.llm_service import LLMService


class _StubProvider:
    """Records calls and returns canned values."""

    def __init__(self, text: str = "resposta", fail: Exception | None = None):
        self._text = text
        self._fail = fail
        self.calls = 0

    @property
    def provider_name(self) -> str:
        return "stub"

    async def generate(self, prompt: str, **_kwargs) -> str:
        self.calls += 1
        if self._fail:
            raise self._fail
        return self._text

    async def analyze_resume(self, resume, job_description, **_kwargs):
        if self._fail:
            raise self._fail
        return {"score": 71}

    async def compare_job(self, resume, job, **_kwargs):
        return {"compatibility_score": 64}

    async def generate_cover_letter(self, resume, job, **_kwargs):
        return "carta"

    async def generate_tailored_resume(self, resume, job, **_kwargs):
        return "curriculo"

    async def answer_question(self, question, context="", **_kwargs):
        return "conselho"

    async def suggest_profile(self, resume, target_role="", **_kwargs):
        return {"headline": "h"}

    async def health_check(self) -> bool:
        return True


class _FakeCache:
    def __init__(self):
        self.store: dict[str, str] = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value


@pytest.mark.asyncio
async def test_operations_delegate_to_the_provider():
    service = LLMService(_StubProvider())

    assert service.provider_name == "stub"
    assert (await service.analyze_resume("cv", "vaga"))["score"] == 71
    assert (await service.compare_job("cv", {}))["compatibility_score"] == 64
    assert await service.generate_cover_letter("cv", {}) == "carta"
    assert await service.generate_tailored_resume("cv", {}) == "curriculo"
    assert await service.answer_question("como?") == "conselho"
    assert (await service.suggest_profile("cv"))["headline"] == "h"
    assert await service.health_check() is True


@pytest.mark.asyncio
async def test_transport_failures_become_a_domain_error():
    """Left unhandled these surface as opaque 500s instead of a 502."""
    service = LLMService(_StubProvider(fail=RuntimeError("connection reset")))

    with pytest.raises(LLMProviderError) as raised:
        await service.generate("oi")
    assert "connection reset" in str(raised.value)


@pytest.mark.asyncio
async def test_a_domain_error_is_not_wrapped_twice():
    service = LLMService(_StubProvider(fail=LLMProviderError("já traduzido")))

    with pytest.raises(LLMProviderError) as raised:
        await service.generate("oi")
    assert str(raised.value) == "já traduzido"


@pytest.mark.asyncio
async def test_a_cache_hit_skips_the_provider(monkeypatch):
    """Caching was implemented and then never exercised by any caller."""
    provider = _StubProvider("primeira")
    service = LLMService(provider)
    cache = _FakeCache()
    monkeypatch.setattr(service, "_get_cache", lambda: _resolve(cache))

    assert await service.generate("prompt", cache_key="k") == "primeira"
    assert provider.calls == 1

    provider._text = "segunda"
    assert await service.generate("prompt", cache_key="k") == "primeira"
    assert provider.calls == 1, "the second call should have been served from cache"


@pytest.mark.asyncio
async def test_calls_without_a_cache_key_always_reach_the_provider(monkeypatch):
    provider = _StubProvider()
    service = LLMService(provider)
    monkeypatch.setattr(service, "_get_cache", lambda: _resolve(_FakeCache()))

    await service.generate("prompt")
    await service.generate("prompt")
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_summarize_keys_the_cache_by_content(monkeypatch):
    """hash() is salted per process, so it cannot key a cache shared across replicas."""
    provider = _StubProvider("resumo")
    service = LLMService(provider)
    cache = _FakeCache()
    monkeypatch.setattr(service, "_get_cache", lambda: _resolve(cache))

    await service.summarize("um texto longo")
    keys = list(cache.store)
    assert len(keys) == 1 and keys[0].startswith("llm:sum:")

    # The same content in a fresh service must produce the same key.
    other = LLMService(_StubProvider("resumo"))
    monkeypatch.setattr(other, "_get_cache", lambda: _resolve(cache))
    await other.summarize("um texto longo")
    assert list(cache.store) == keys


async def _resolve(value):
    return value
