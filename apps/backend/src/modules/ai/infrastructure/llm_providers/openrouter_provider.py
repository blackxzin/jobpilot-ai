"""OpenRouter LLM Provider implementation."""
from __future__ import annotations

import os

from core.config import settings
from modules.ai.infrastructure.llm_providers.openai_compatible import OpenAICompatibleProvider

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider(OpenAICompatibleProvider):
    """Provider for OpenRouter, an aggregator that routes to many models."""

    def __init__(self, api_key: str | None = None, model: str = "openai/gpt-4o"):
        super().__init__(
            api_key=api_key or os.getenv("OPENROUTER_API_KEY", settings.OPENROUTER_API_KEY),
            model=model,
            base_url=OPENROUTER_BASE_URL,
        )

    @property
    def provider_name(self) -> str:
        return "openrouter"
