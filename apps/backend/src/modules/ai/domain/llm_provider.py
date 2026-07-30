"""LLM Provider interface (port/domain)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncGenerator


class LLMProvider(ABC):
    """Abstract interface for all LLM providers.

    Every provider must implement this interface exactly.
    The LLMService uses Strategy pattern — swap providers without changing calling code.

    Design principle:
    The calling code (use_cases) depends only on this abstract interface.
    Provider implementations live in infrastructure — they never leak into domain.
    """

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from a prompt, non-streaming."""
        ...

    @abstractmethod
    async def stream_generate(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Generate text with streaming response (SSE)."""
        ...

    @abstractmethod
    async def summarize(self, text: str, **kwargs) -> str:
        """Summarize the given text."""
        ...

    @abstractmethod
    async def analyze_resume(self, resume: str, job_description: str, **kwargs) -> dict:
        """Analyze resume against a job description.

        Returns dict with:
            - score: int (0-100)
            - matched_skills: list[str]
            - missing_skills: list[str]
            - suggestions: list[str]
            - strengths: list[str]
        """
        ...

    @abstractmethod
    async def compare_job(self, resume: str, job: dict, **kwargs) -> dict:
        """Compare resume to a job posting for matching.

        Returns dict with:
            - compatibility_score: int (0-100)
            - match_reasons: list[dict with text, type (match|gap)]
            - suggestions: list[str]
        """
        ...

    @abstractmethod
    async def generate_cover_letter(self, resume: str, job: dict) -> str:
        """Generate a personalized cover letter for a specific job."""
        ...

    @abstractmethod
    async def generate_tailored_resume(self, resume: str, job: dict) -> str:
        """Generate a resume tailored to a specific job description.

        Adapts the candidate's existing experience to highlight relevant
        skills and achievements for the target role.
        """
        ...

    @abstractmethod
    async def answer_question(self, question: str, context: str = "") -> str:
        """Answer a career-related question using optional user context."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is reachable and configured correctly."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier string (e.g., 'openai', 'anthropic')."""
        ...