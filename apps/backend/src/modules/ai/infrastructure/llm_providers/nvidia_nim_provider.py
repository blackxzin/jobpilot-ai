"""NVIDIA NIM LLM Provider implementation.

NIM exposes an OpenAI-compatible API, so the credential is an OpenAI-shaped
key kept in `OPENAI_API_KEY` and only the base URL differs.
"""
from __future__ import annotations

from core.config import settings
from modules.ai.infrastructure.llm_providers.openai_compatible import OpenAICompatibleProvider


class NvidiaNimProvider(OpenAICompatibleProvider):
    """Provider for the NVIDIA NIM hosted inference API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "",
        base_url: str | None = None,
    ):
        super().__init__(
            api_key=api_key or settings.OPENAI_API_KEY,
            model=model or settings.NVIDIA_NIM_MODEL,
            base_url=base_url or settings.NVIDIA_NIM_ENDPOINT,
        )

    @property
    def provider_name(self) -> str:
        return "nvidia_nim"
