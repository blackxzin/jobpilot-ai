"""NVIDIA NIM LLM Provider implementation."""
from __future__ import annotations

import os
from typing import AsyncGenerator

from openai import AsyncOpenAI

from modules.ai.domain.llm_provider import LLMProvider
from core.config import settings

class NvidiaNimProvider(LLMProvider):
    """Provider for NVIDIA NIM API (uses OpenAI-compatible endpoint).

    NVIDIA NIM provides hosted LLMs with a standard OpenAI-compatible API.
    This is the default provider for development environments.
    """

    def __init__(self, api_key: str | None = None, model: str = "meta/llama-3.2-3b-instruct", base_url: str | None = None):
        self._provider_name = "nvidia_nim"
        self._model = model
        api_key = api_key or settings.OPENAI_API_KEY  # NIM uses OpenAI-compatible key
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=(base_url or settings.NVIDIA_NIM_ENDPOINT),
        )

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
        return await self.generate(f"Summarize concisely:\n\n{text}", **kwargs)

    async def analyze_resume(self, resume: str, job_description: str, **kwargs) -> dict:
        prompt = (
            f'Analyze resume vs job. Return ONLY JSON: '
            f'score(0-100), matched_skills[], missing_skills[], suggestions[], strengths[]'
            f'\n\nRESUME:\n{resume}\n\nJOB:\n{job_description}'
        )
        result = await self.generate(prompt, **kwargs)
        return self._parse_json(result)

    async def compare_job(self, resume: str, job: dict, **kwargs) -> dict:
        prompt = (
            f'Compare resume to job. Return ONLY JSON: '
            f'compatibility_score(0-100), match_reasons[{{text,type}}], suggestions[]'
            f'\n\nRESUME:\n{resume}\n\nJOB: {job.get("title","")} at {job.get("company","")}'
        )
        result = await self.generate(prompt, **kwargs)
        return self._parse_json(result)

    async def generate_cover_letter(self, resume: str, job: dict, **kwargs) -> str:
        prompt = (
            f'Write a cover letter (3 paragraphs, max 400 words).\n\n'
            f'Resume: {resume[:2000]}\n'
            f'Job: {job.get("title","")} at {job.get("company","")}\n'
            f'Requirements: {", ".join(job.get("requirements", []))}\n'
            f'Reference resume only. Never invent.'
        )
        return await self.generate(prompt, **kwargs)

    async def answer_question(self, question: str, context: str = "", **kwargs) -> str:
        prompt = f'You are a career coach.\n{f"Context: {context}\n" if context else ""}Question: {question}\nProvide helpful career advice.'
        return await self.generate(prompt, **kwargs)

    async def generate_tailored_resume(self, resume: str, job: dict) -> str:
        prompt = (
            f'Tailor this resume for the target job. Return ONLY the tailored resume.\n\n'
            f'ORIGINAL RESUME:\n{resume}\n\n'
            f'TARGET: {job.get("title","")} at {job.get("company","")}\n'
            f'DESC: {job.get("description","")[:500]}\n\n'
            f'Keep all experience. Rewrite bullets for relevance. Add professional summary + relevant skills. Markdown.'
        )
        return await self.generate(prompt)

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
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
