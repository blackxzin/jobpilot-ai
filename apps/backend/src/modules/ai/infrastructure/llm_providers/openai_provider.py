"""OpenAI LLM Provider implementation."""
from __future__ import annotations

import os
from typing import AsyncGenerator

from openai import AsyncOpenAI

from modules.ai.domain.llm_provider import LLMProvider
from core.config import settings

class OpenAIProvider(LLMProvider):
    """Provider for OpenAI's Chat Completions API."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o", base_url: str | None = None):
        self._provider_name = "openai"
        kwargs = dict(
            api_key=api_key or os.getenv("OPENAI_API_KEY", settings.OPENAI_API_KEY),
        )
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**kwargs)
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return self._provider_name

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

    async def summarize(self, text: str, **kwargs) -> str:
        prompt = f"Summarize the following text concisely:\n\n{text}"
        return await self.generate(prompt, **kwargs)

    async def analyze_resume(self, resume: str, job_description: str, **kwargs) -> dict:
        from core.logger import get_logger
        logger = get_logger(__name__)

        prompt = f"""Analyze the candidate's resume against the job description below.

RESUME:
{resume}

JOB DESCRIPTION:
{job_description}

Return a JSON object with these exact keys:
- "score": integer 0-100 representing overall compatibility
- "matched_skills": list of skills the candidate HAS that the job requires
- "missing_skills": list of skills the job requires that the candidate does NOT have
- "suggestions": list of actionable suggestions to improve compatibility
- "strengths": list of strong matching points

Example response format:
{{
  "score": 85,
  "matched_skills": ["Python", "React", "SQL"],
  "missing_skills": ["Docker", "AWS"],
  "suggestions": ["Learn Docker to increase compatibility by 10%", "Get AWS certification"],
  "strengths": ["Strong Python backend experience", "5+ years React"]
}}"""

        logger.info("analyzing_resume_with_openai", model=self._model)
        result = await self.generate(prompt, **kwargs)

        # Try to parse JSON from the response
        try:
            import json
            # Find JSON block in response
            start = result.index("{")
            end = result.rindex("}") + 1
            parsed = json.loads(result[start:end])
            return parsed
        except (ValueError, IndexError):
            logger.warning("failed_to_parse_json_from_openai_response")
            # Return raw structured fallback
            return {
                "score": 0,
                "matched_skills": [],
                "missing_skills": [],
                "suggestions": ["Manual review recommended"],
                "strengths": [],
                "raw_response": result,
            }

    async def compare_job(self, resume: str, job: dict, **kwargs) -> dict:
        from core.logger import get_logger
        logger = get_logger(__name__)

        job_desc = job.get("description", "")
        job_title = job.get("title", "")
        job_requirements = job.get("requirements", [])
        job_skills = job.get("skills", [])

        prompt = f"""Compare this candidate's resume to a job posting.

JOB TITLE: {job_title}
JOB DESCRIPTION: {job_desc}
REQUIRED TECHNOLOGIES: {', '.join(job_skills)}
REQUIREMENTS: {job_requirements}

RESUME:
{resume}

Return JSON with exact keys:
- "compatibility_score": 0-100 integer
- "match_reasons": list of {{text, type: "match" | "gap"}}
- "suggestions": list of strings

Be honest and specific — never inflate the score."""

        logger.info("comparing_job_with_openai", model=self._model, job_title=job_title)
        result = await self.generate(prompt, **kwargs)

        try:
            import json
            start = result.index("{")
            end = result.rindex("}") + 1
            parsed = json.loads(result[start:end])
            return parsed
        except (ValueError, IndexError):
            return {
                "compatibility_score": 0,
                "match_reasons": [],
                "suggestions": ["Manual review recommended"],
                "raw_response": result,
            }

    async def generate_cover_letter(self, resume: str, job: dict, **kwargs) -> str:
        from core.logger import get_logger
        logger = get_logger(__name__)

        company_name = job.get("company", "the company")
        job_title = job.get("title", "the position")
        job_desc = job.get("description", "")
        job_requirements = job.get("requirements", [])

        prompt = f"""Write a personalized cover letter for a job application.

The candidate's resume:
{resume}

Applying for: {job_title} at {company_name}
Job requirements: {', '.join(job_requirements)}
Job description: {job_desc[:500]}

The cover letter should:
- Be 3-4 paragraphs
- Reference specific relevant experience from the resume
- Show genuine interest in the company
- Be professional but warm
- Not invent any experience that is not in the resume
- Be concise (max 400 words)"""

        logger.info("generating_cover_letter_with_openai", model=self._model, company=company_name)
        return await self.generate(prompt)

    async def answer_question(self, question: str, context: str = "") -> str:
        prompt = f"""You are a career coach and job search advisor.

{'Context about the user:\n' + context if context else ''}

Question: {question}

Provide a helpful, detailed answer based on best practices in job searching and career development."""

        return await self.generate(prompt)

    async def health_check(self) -> bool:
        try:
            # Simple check: try to list models (lightweight API call)
            await self._client.models.list()
            return True
        except Exception:
            return False
