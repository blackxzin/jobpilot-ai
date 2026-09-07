"""Shared transport for every OpenAI-compatible Chat Completions endpoint.

OpenAI, NVIDIA NIM and OpenRouter all speak the same wire protocol and differ
only in base URL, credential and default model. Keeping three byte-identical
`generate`/`stream_generate`/`health_check` implementations meant a fix to the
streaming loop had to be made three times.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from core.config import settings
from modules.ai.infrastructure.llm_providers.base import PromptDrivenProvider


class OpenAICompatibleProvider(PromptDrivenProvider):
    """Base adapter for any endpoint implementing the OpenAI chat API."""

    def __init__(self, api_key: str | None, model: str, base_url: str | None = None):
        self._model = model
        client_kwargs: dict = {
            "api_key": api_key or "",
            "timeout": settings.LLM_TIMEOUT_SECONDS,
            "max_retries": settings.LLM_MAX_RETRIES,
        }
        if base_url:
            client_kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**client_kwargs)

    @property
    def model(self) -> str:
        return self._model

    async def generate(self, prompt: str, **kwargs) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            **kwargs,
        )
        return response.choices[0].message.content or ""

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            **kwargs,
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content is not None:
                yield content

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False
