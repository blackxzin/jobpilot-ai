"""Anthropic Claude LLM Provider implementation."""
from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from anthropic import AsyncAnthropic

from core.config import settings
from modules.ai.infrastructure.llm_providers.base import PromptDrivenProvider

DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.7


class AnthropicProvider(PromptDrivenProvider):
    """Provider for the Anthropic Claude Messages API."""

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-20250514"):
        self._client = AsyncAnthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY", settings.ANTHROPIC_API_KEY),
            timeout=settings.LLM_TIMEOUT_SECONDS,
            max_retries=settings.LLM_MAX_RETRIES,
        )
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return "anthropic"

    async def generate(self, prompt: str, **kwargs) -> str:
        message = await self._client.messages.create(
            model=self._model,
            max_tokens=kwargs.get("max_tokens", DEFAULT_MAX_TOKENS),
            temperature=kwargs.get("temperature", DEFAULT_TEMPERATURE),
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in message.content if hasattr(block, "text"))

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=kwargs.get("max_tokens", DEFAULT_MAX_TOKENS),
            temperature=kwargs.get("temperature", DEFAULT_TEMPERATURE),
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def health_check(self) -> bool:
        try:
            await self._client.messages.create(
                model=self._model,
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False
