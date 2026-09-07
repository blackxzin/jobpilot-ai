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

# Analyses of the same input are stable and expensive; an hour is long enough
# to help and short enough that an edited resume is not served stale.
CACHE_TTL_SECONDS = 3600


def _explain(provider: str, operation: str, exc: Exception) -> str:
    """Turn a provider exception into something the user can act on.

    Hosted providers retire models on a schedule and answer with an opaque
    HTTP error. Reporting only "provider failed" left the user with no idea
    that the fix is to pick a different model.
    """
    detail = str(exc)
    lowered = detail.lower()

    if "end of life" in lowered or "no longer available" in lowered or "410" in detail:
        return (
            f"O modelo configurado para '{provider}' foi descontinuado pelo provedor. "
            "Escolha outro modelo em Configurações → IA."
        )
    if "401" in detail or "unauthorized" in lowered or "invalid api key" in lowered:
        return f"A chave de API de '{provider}' foi recusada. Verifique-a em Configurações → IA."
    if "429" in detail or "rate limit" in lowered:
        return f"O provedor '{provider}' está limitando as requisições. Tente de novo em instantes."
    if "timeout" in lowered or "timed out" in lowered:
        return f"O provedor '{provider}' não respondeu a tempo. Tente de novo."

    return f"O provedor '{provider}' falhou em {operation}: {detail}"


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
            raise LLMProviderError(_explain(self.provider_name, operation, exc)) from exc

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
            await cache.set(f"llm:{cache_key}", result, ex=CACHE_TTL_SECONDS)

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

    async def suggest_profile(self, resume: str, target_role: str = "", **kwargs) -> dict:
        """Suggest professional-profile positioning from the user's own resume."""
        logger.info("llm_suggest_profile", provider=self.provider_name)
        return await self._call(
            "suggest_profile",
            lambda: self._provider.suggest_profile(resume, target_role, **kwargs),
        )

    async def health_check(self) -> bool:
        """Check provider health."""
        return await self._provider.health_check()
