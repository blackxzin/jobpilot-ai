"""Unit tests for the shared cover-letter prompt builder."""
from __future__ import annotations

from modules.ai.infrastructure.llm_providers.prompt_builder import build_cover_letter_prompt


def test_default_language_and_tone():
    prompt = build_cover_letter_prompt("Python dev, 5 years", {"title": "Backend Engineer", "company": "Acme"})
    assert "Brazilian Portuguese" in prompt
    assert "Professional but warm." in prompt
    assert "Backend Engineer" in prompt
    assert "Acme" in prompt


def test_language_and_tone_are_configurable():
    prompt = build_cover_letter_prompt("Python dev", {"title": "Dev", "company": "Acme"}, language="en", tone="enthusiastic")
    assert "Brazilian Portuguese" not in prompt
    assert "English" in prompt
    assert "Enthusiastic" in prompt


def test_requirements_and_skills_are_woven_into_prompt():
    job = {"title": "Dev", "company": "Acme", "requirements": ["5+ years Python"], "skills": ["FastAPI"]}
    prompt = build_cover_letter_prompt("resume text", job)
    assert "5+ years Python" in prompt
    assert "FastAPI" in prompt


def test_missing_job_fields_use_fallbacks():
    prompt = build_cover_letter_prompt("resume text", {})
    assert "the position" in prompt
    assert "the company" in prompt
