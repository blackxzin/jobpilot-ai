"""Anthropic Claude LLM Provider implementation."""
from __future__ import annotations

import os
from typing import AsyncGenerator

from anthropic import AsyncAnthropic

from modules.ai.domain.llm_provider import LLMProvider
from core.config import settings

class AnthropicProvider(LLMProvider):
    """Provider for Anthropic Claude API (messages API)."""

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-20250514"):
        self._provider_name = "anthropic"
        self._client = AsyncAnthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY", settings.ANTHROPIC_API_KEY),
        )
        self._model = model

    @property
    def model(self) -> str:

    
        return self._provider_name
        return self._model

    @property
    def provider_name(self) -> str:
        return self._provider_name

    async def generate(self, prompt: str, **kwargs) -> str:
        # Map kwargs to Claude API params
        max_tokens = kwargs.get("max_tokens", 4096)
        temperature = kwargs.get("temperature", 0.7)

        message = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "user", "content": prompt}
            ],
        )
        # Extract text from content blocks
        texts = []
        for block in message.content:
            if hasattr(block, "text"):
                texts.append(block.text)
        return "".join(texts)

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        max_tokens = kwargs.get("max_tokens", 4096)
        temperature = kwargs.get("temperature", 0.7)

        with self._client.messages.stream(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def summarize(self, text: str, **kwargs) -> str:
        prompt = f"""Summarize the following text concisely. Keep key points, remove filler.

TEXT:
{text}"""
        return await self.generate(prompt, **kwargs)

    async def analyze_resume(self, resume: str, job_description: str, **kwargs) -> dict:
        prompt = f"""You are an expert ATS (Applicant Tracking System) reviewer and career coach.

Analyze this candidate's resume against the job description and return ONLY valid JSON:

RESUME:
{resume}

JOB DESCRIPTION:
{job_description}

Return JSON with exactly these keys:
- "score": integer 0-100
- "matched_skills": list of strings (skills candidate has that job requires)
- "missing_skills": list of strings (skills job requires that candidate lacks)
- "suggestions": list of specific, actionable suggestions
- "strengths": list of strong matching points

Never invent or guess skills not mentioned in the resume or job description."""

        result = await self.generate(prompt, **kwargs)
        return self._parse_json(result)

    async def compare_job(self, resume: str, job: dict, **kwargs) -> dict:
        job_title = job.get("title", "")
        company = job.get("company", "")
        job_desc = job.get("description", "")
        job_skills = job.get("skills", [])
        job_requirements = job.get("requirements", [])

        prompt = f"""Compare this candidate to a job posting. Return ONLY valid JSON.

RESUME:
{resume}

JOB: {job_title} at {company}
DESCRIPTION: {job_desc}
REQUIRED TECHNOLOGIES: {', '.join(job_skills)}
ALL REQUIREMENTS: {job_requirements}

Return JSON with:
- "compatibility_score": integer 0-100
- "match_reasons": list of {{text: string, type: "match" or "gap"}}
- "suggestions": list of strings

Be honest and specific."""

        result = await self.generate(prompt, **kwargs)
        return self._parse_json(result)

    async def generate_cover_letter(self, resume: str, job: dict, **kwargs) -> str:
        company = job.get("company", "")
        job_title = job.get("title", "")
        job_desc = job.get("description", "")
        job_requirements = job.get("requirements", [])

        prompt = f"""Write a personalized cover letter (3-4 paragraphs, max 400 words).

Resume:
{resume}

Applying for: {job_title} at {company}
Requirements: {', '.join(job_requirements)}
Description: {job_desc[:500]}

Rules:
- Reference specific experience from the resume (never invent)
- Show genuine interest
- Professional but warm tone
- Be concise"""

        return await self.generate(prompt, **kwargs)

    async def answer_question(self, question: str, context: str = "") -> str:
        prompt = f"""You are a career coach and job search advisor.

{'User context: ' + context + '\n' if context else ''}
Question: {question}

Give a helpful, detailed answer about job searching and career development."""

        return await self.generate(prompt, **kwargs)

    async def generate_tailored_resume(self, resume: str, job: dict) -> str:
        job_title = job.get("title", "")
        company = job.get("company", "")
        job_desc = job.get("description", "")

        prompt = f"""You are a professional resume writer. Tailor the candidate's resume for a specific job.

CANDIDATE'S ORIGINAL RESUME:
{resume}

TARGET JOB: {job_title} at {company}
JOB DESCRIPTION: {job_desc}

Write a tailored resume that:
1. Keeps ALL experience and education from the original — never invent
2. Rewrites bullet points to emphasize skills relevant to this job
3. Adds a "Relevant Skills" section highlighting matching keywords
4. Includes a professional summary (2-3 sentences) tailored to this role
5. Uses same contact info
6. Clean markdown format

Return ONLY the resume content."""
        return await self.generate(prompt)

    async def health_check(self) -> bool:
        try:
            # Verify by making a small call
            await self._client.messages.create(
                model=self._model,
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )
            return True
        except Exception:
            return False

    def _parse_json(self, text: str) -> dict:
        """Extract and parse JSON from potentially markdown-wrapped response."""
        import json
        import re
        try:
            # Try direct parse first
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Try to find JSON block (between ```json and ```, or raw braces)
        block_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if block_match:
            try:
                return json.loads(block_match.group(1))
            except json.JSONDecodeError:
                pass
        # Try raw braces
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
