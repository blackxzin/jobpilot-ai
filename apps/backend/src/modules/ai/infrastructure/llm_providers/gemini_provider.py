"""Google Gemini LLM Provider implementation."""
from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from core.config import settings
from modules.ai.infrastructure.llm_providers.base import PromptDrivenProvider

DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.7


class GeminiProvider(PromptDrivenProvider):
    """Provider for the Google Gemini API."""

    def __init__(self, api_key: str | None = None, model: str = "gemini-2.0-flash"):
        # Imported here rather than at module scope: the SDK emits a
        # deprecation warning on import, which should not fire for users who
        # never select Gemini.
        from google.generativeai import GenerativeModel, configure

        self._model_name = model
        resolved_key = api_key or os.getenv("GEMINI_API_KEY", settings.GEMINI_API_KEY)
        if resolved_key:
            configure(api_key=resolved_key)
        self._client = GenerativeModel(model)

    @property
    def model(self) -> str:
        return self._model_name

    @property
    def provider_name(self) -> str:
        return "gemini"

    def _generation_config(self, kwargs: dict) -> dict:
        return {
            "temperature": kwargs.get("temperature", DEFAULT_TEMPERATURE),
            "max_output_tokens": kwargs.get("max_tokens", DEFAULT_MAX_TOKENS),
        }

    async def generate(self, prompt: str, **kwargs) -> str:
        response = await self._client.generate_content_async(
            prompt, generation_config=self._generation_config(kwargs)
        )
        return response.text or ""

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        response = await self._client.generate_content_async(
            prompt, stream=True, generation_config=self._generation_config(kwargs)
        )
        async for chunk in response:
            if chunk.text:
                yield chunk.text

    async def health_check(self) -> bool:
        try:
            await self._client.generate_content_async(
                "ping", generation_config={"max_output_tokens": 1}
            )
            return True
        except Exception:
            return False
