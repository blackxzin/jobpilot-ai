"""OpenAI LLM Provider implementation."""
from __future__ import annotations

import os

from core.config import settings
from modules.ai.infrastructure.llm_providers.openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    """Provider for OpenAI's Chat Completions API."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o", base_url: str | None = None):
        super().__init__(
            api_key=api_key or os.getenv("OPENAI_API_KEY", settings.OPENAI_API_KEY),
            model=model,
            base_url=base_url,
        )

    @property
    def provider_name(self) -> str:
        return "openai"
