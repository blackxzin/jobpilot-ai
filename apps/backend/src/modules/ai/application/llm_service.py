"""LLM Service — core application service that uses LLM providers.

This service is the single entry point for all AI operations in the application.
It uses the Strategy pattern: the concrete provider is injected at runtime
based on the user's configuration. No application logic depends on a specific provider.

Design:
- The service receives an LLMProvider (domain interface) — never a concrete class.
- The provider is selected by the factory based on user config.
- All AI calls go through this service for logging, caching, and cost tracking.
"""
from __future__ import annotations

import hashlib
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import TypeVar

from core.exceptions import LLMProviderError
from core.logger import get_logger
from modules.ai.domain.llm_provider import LLMProvider

logger = get_logger(__name__)

T = TypeVar("T")


class LLMService:
    """Application service that wraps LLM providers with caching and logging."""

    def __init__(self, provider: LLMProvider):
        self._provider = provider
        self._cache = None  # lazy-initialized via _get_cache()

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name

    async def _call(self, operation: str, call: Callable[[], Awaitable[T]]) -> T:
        """Run a provider call, converting failures into a domain error.

        Providers raise transport-specific exceptions (timeouts, auth errors,
        rate limits). Left unhandled they surface as opaque 500s, so they are
        translated into LLMProviderError, which the API maps to 502.
        """
        try:
            return await call()
        except LLMProviderError:
            raise
        except Exception as exc:
            logger.error(
                "llm_call_failed",
                provider=self.provider_name,
                operation=operation,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise LLMProviderError(
                f"LLM provider '{self.provider_name}' failed during {operation}: {exc}"
            ) from exc

    async def _get_cache(self):
        """Lazy-init Redis client."""
        if self._cache is None:
            from core.redis_client import get_redis
            self._cache = await get_redis()
        return self._cache

    async def generate(self, prompt: str, cache_key: str | None = None, **kwargs) -> str:
        """Generate text, optionally using Redis cache.

        Args:
            prompt: The input prompt.
            cache_key: Optional cache key. If provided and cache hit, returns cached result.
        """
        if cache_key:
            cache = await self._get_cache()
            cached = await cache.get(f"llm:{cache_key}")
            if cached:
                logger.info("llm_cache_hit", provider=self.provider_name, key=cache_key)
                return cached

        result = await self._call("generate", lambda: self._provider.generate(prompt, **kwargs))

        if cache_key:
            cache = await self._get_cache()
            await cache.setex(f"llm:{cache_key}", 3600, result)  # 1h TTL

        logger.info("llm_generate", provider=self.provider_name, cached=cache_key is not None)
        return result

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Stream generation response."""
        async for chunk in self._provider.stream_generate(prompt, **kwargs):
            yield chunk

    async def summarize(self, text: str, cache_key: str | None = None, **kwargs) -> str:
        # Built-in hash() is salted per process, so it cannot key a shared cache.
        digest = hashlib.sha256(text.encode()).hexdigest()[:32]
        return await self.generate(
            f"Summarize concisely:\n\n{text}",
            cache_key=f"sum:{digest}" if cache_key is None else cache_key,
            **kwargs,
        )

    async def analyze_resume(self, resume: str, job_description: str, **kwargs) -> dict:
        """Analyze resume against job description."""
        logger.info("llm_analyze_resume", provider=self.provider_name)
        result = await self._call(
            "analyze_resume", lambda: self._provider.analyze_resume(resume, job_description, **kwargs)
        )
        logger.info("llm_analyze_resume_complete", provider=self.provider_name, score=result.get("score"))
        return result

    async def compare_job(self, resume: str, job: dict, **kwargs) -> dict:
        """Compare resume to a job posting."""
        logger.info("llm_compare_job", provider=self.provider_name, job_title=job.get("title"))
        result = await self._call("compare_job", lambda: self._provider.compare_job(resume, job, **kwargs))
        logger.info("llm_compare_job_complete", provider=self.provider_name, score=result.get("compatibility_score"))
        return result

    async def generate_cover_letter(self, resume: str, job: dict, **kwargs) -> str:
        """Generate a personalized cover letter."""
        logger.info("llm_generate_cover_letter", provider=self.provider_name, company=job.get("company"))
        result = await self._call(
            "generate_cover_letter", lambda: self._provider.generate_cover_letter(resume, job, **kwargs)
        )
        logger.info("llm_generate_cover_letter_complete", provider=self.provider_name, length=len(result))
        return result

    async def answer_question(self, question: str, context: str = "", **kwargs) -> str:
        """Answer a career-related question."""
        return await self._call(
            "answer_question", lambda: self._provider.answer_question(question, context, **kwargs)
        )

    async def generate_tailored_resume(self, resume: str, job: dict, **kwargs) -> str:
        """Generate a resume tailored to a specific job."""
        logger.info("llm_tailor_resume", provider=self.provider_name, job_title=job.get("title"))
        result = await self._call(
            "generate_tailored_resume", lambda: self._provider.generate_tailored_resume(resume, job, **kwargs)
        )
        logger.info("llm_tailor_resume_complete", provider=self.provider_name, length=len(result))
        return result

    async def health_check(self) -> bool:
        """Check provider health."""
        return await self._provider.health_check()


# ── Convenience functions ────────────────────────────────────────────────
# These use the factory for quick access when provider is not yet injected

async def quick_generate(prompt: str, provider_name: str = "openai", model: str = "") -> str:
    """One-shot generate with auto provider selection."""
    from modules.ai.infrastructure.providers.factory import LLMProviderFactory
    provider = LLMProviderFactory.create(provider_name, model=model)
    service = LLMService(provider)
    return await service.generate(prompt)


async def quick_analyze_resume(resume: str, job_desc: str, provider_name: str = "openai") -> dict:
    """One-shot resume analysis."""
    from modules.ai.infrastructure.providers.factory import LLMProviderFactory
    provider = LLMProviderFactory.create(provider_name)
    service = LLMService(provider)
    return await service.analyze_resume(resume, job_desc)