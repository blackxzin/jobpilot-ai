"""Base class implementing every prompt-driven capability once.

All six vendor adapters differ only in how they turn a prompt into text. The
resume analysis, job comparison, cover letter, tailored resume and career Q&A
were nonetheless copy-pasted into each of them, which meant six subtly
different prompts and six copies of the JSON parser. Improving a prompt in one
place silently left five providers behind.

Concrete providers now implement the transport (`generate`, `stream_generate`,
`health_check`, `provider_name`) and inherit everything else.
"""
from __future__ import annotations

from abc import abstractmethod

from modules.ai.domain.llm_provider import LLMProvider
from modules.ai.infrastructure.llm_providers.json_parsing import parse_json_response
from modules.ai.infrastructure.llm_providers.prompt_builder import (
    build_analyze_resume_prompt,
    build_career_answer_prompt,
    build_compare_job_prompt,
    build_cover_letter_prompt,
    build_tailored_resume_prompt,
)

# Resumes are pasted whole into prompts. Truncating keeps a long CV from
# blowing the context window (and the bill) on every provider.
MAX_RESUME_CHARS = 6000


class PromptDrivenProvider(LLMProvider):
    """Implements the provider port on top of a single `generate` primitive."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    async def summarize(self, text: str, **kwargs) -> str:
        return await self.generate(f"Summarize the following text concisely:\n\n{text}", **kwargs)

    async def analyze_resume(self, resume: str, job_description: str, **kwargs) -> dict:
        prompt = build_analyze_resume_prompt(resume or "", job_description or "")
        return parse_json_response(await self.generate(prompt, **kwargs))

    async def compare_job(self, resume: str, job: dict, **kwargs) -> dict:
        prompt = build_compare_job_prompt(resume or "", job or {})
        return parse_json_response(await self.generate(prompt, **kwargs))

    async def generate_cover_letter(
        self, resume: str, job: dict, language: str = "pt-BR", tone: str = "professional", **kwargs
    ) -> str:
        prompt = build_cover_letter_prompt(
            (resume or "")[:MAX_RESUME_CHARS], job or {}, language=language, tone=tone
        )
        return await self.generate(prompt, **kwargs)

    async def generate_tailored_resume(self, resume: str, job: dict, **kwargs) -> str:
        prompt = build_tailored_resume_prompt(resume or "", job or {})
        return await self.generate(prompt, **kwargs)

    async def answer_question(self, question: str, context: str = "", **kwargs) -> str:
        return await self.generate(build_career_answer_prompt(question, context), **kwargs)
