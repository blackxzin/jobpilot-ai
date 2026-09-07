"""Ollama LLM Provider implementation — local, self-hosted models."""
from __future__ import annotations

import json
from collections.abc import AsyncGenerator

import httpx

from core.config import settings
from modules.ai.infrastructure.llm_providers.base import PromptDrivenProvider

DEFAULT_MAX_TOKENS = 2048
DEFAULT_TEMPERATURE = 0.7


class OllamaProvider(PromptDrivenProvider):
    """Provider for an Ollama server (no API key; base URL only)."""

    def __init__(self, base_url: str | None = None, model: str = "llama3.1"):
        self._base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self._model = model
        self._client = httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS)

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return "ollama"

    def _payload(self, prompt: str, stream: bool, kwargs: dict) -> dict:
        return {
            "model": self._model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": kwargs.get("temperature", DEFAULT_TEMPERATURE),
                "num_predict": kwargs.get("max_tokens", DEFAULT_MAX_TOKENS),
            },
        }

    async def generate(self, prompt: str, **kwargs) -> str:
        response = await self._client.post(
            f"{self._base_url}/api/generate", json=self._payload(prompt, False, kwargs)
        )
        response.raise_for_status()
        return response.json().get("response", "")

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        async with self._client.stream(
            "POST", f"{self._base_url}/api/generate", json=self._payload(prompt, True, kwargs)
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                token = json.loads(line).get("response", "")
                if token:
                    yield token

    async def health_check(self) -> bool:
        try:
            response = await self._client.get(f"{self._base_url}/api/tags")
            return response.is_success
        except Exception:
            return False
