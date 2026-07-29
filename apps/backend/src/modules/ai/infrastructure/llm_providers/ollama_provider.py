"""Ollama LLM Provider implementation."""
from __future__ import annotations

import os
from typing import AsyncGenerator

import httpx

from modules.ai.domain.llm_provider import LLMProvider
from core.config import settings


class OllamaProvider(LLMProvider):
    """Provider for Ollama (local LLM server)."""

    def __init__(self, base_url: str | None = None, model: str = "llama3.1"):
        self.provider_name = "ollama"
        self._base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self._model = model
        self._client = httpx.AsyncClient(timeout=120.0)

    @property
    def model(self) -> str:
        return self._model

    async def generate(self, prompt: str, **kwargs) -> str:
        response = await self._client.post(
            f"{self._base_url}/api/generate",
            json={
                "model": self._model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "num_predict": kwargs.get("max_tokens", 2048),
                },
            },
        )
        response.raise_for_status()
        return response.json().get("response", "")

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        async with self._client.stream(
            "POST",
            f"{self._base_url}/api/generate",
            json={
                "model": self._model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "num_predict": kwargs.get("max_tokens", 2048),
                },
            },
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    import json
                    data = json.loads(line)
                    token = data.get("response", "")
                    if token:
                        yield token

    async def summarize(self, text: str, **kwargs) -> str:
        prompt = f"Summarize concisely:\n\n{text}"
        return await self.generate(prompt, **kwargs)

    async def analyze_resume(self, resume: str, job_description: str, **kwargs) -> dict:
        prompt = f"""Analyze resume vs job description. Return ONLY valid JSON:

RESUME:
{resume}

JOB:
{job_description}

JSON keys: score (0-100), matched_skills, missing_skills, suggestions, strengths"""
        result = await self.generate(prompt, **kwargs)
        return self._parse_json(result)

    async def compare_job(self, resume: str, job: dict, **kwargs) -> dict:
        job_title = job.get("title", "")
        company = job.get("company", "")
        job_desc = job.get("description", "")
        job_skills = job.get("skills", [])

        prompt = f"""Compare resume vs job. Return ONLY valid JSON:

RESUME:
{resume}

JOB: {job_title} at {company}
SKILLS NEEDED: {', '.join(job_skills)}
DESC: {job_desc[:500]}

JSON keys: compatibility_score (0-100), match_reasons [{{text, type}}], suggestions"""
        result = await self.generate(prompt, **kwargs)
        return self._parse_json(result)

    async def generate_cover_letter(self, resume: str, job: dict, **kwargs) -> str:
        company = job.get("company", "")
        job_title = job.get("title", "")
        job_requirements = job.get("requirements", [])

        prompt = f"""Write a cover letter (3 paragraphs max 400 words).

Resume:
{resume}

Job: {job_title} at {company}
Requirements: {', '.join(job_requirements)}

Rules: Reference resume experiences only. Never invent. Professional tone."""
        return await self.generate(prompt, **kwargs)

    async def answer_question(self, question: str, context: str = "") -> str:
        prompt = f"""You are a career coach.

{'User context: ' + context + '\n' if context else ''}
Question: {question}

Provide a helpful answer about job searching and career development."""
        return await self.generate(prompt, **kwargs)

    async def health_check(self) -> bool:
        try:
            response = await self._client.get(f"{self._base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    def _parse_json(self, text: str) -> dict:
        import json
        import re
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        block_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if block_match:
            try:
                return json.loads(block_match.group(1))
            except json.JSONDecodeError:
                pass
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            return {"error": "Failed to parse LLM response", "raw": text}