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


# ── ATS analysis ────────────────────────────────────────────────────────────

def test_analyze_prompt_carries_both_documents():
    from modules.ai.infrastructure.llm_providers.prompt_builder import build_analyze_resume_prompt

    prompt = build_analyze_resume_prompt("CURRICULO AQUI", "VAGA AQUI")
    assert "CURRICULO AQUI" in prompt
    assert "VAGA AQUI" in prompt
    for key in ("score", "matched_skills", "missing_skills", "suggestions", "strengths"):
        assert key in prompt


def test_long_inputs_are_truncated():
    """Resumes are pasted whole; an unbounded prompt blows the context window.

    Sentinels rather than character counts: the prompt template has its own
    letters, so counting occurrences measures the template too.
    """
    from modules.ai.infrastructure.llm_providers.prompt_builder import build_analyze_resume_prompt

    resume = "a" * 5900 + "RESUME_KEPT" + "a" * 5000 + "RESUME_CUT"
    job = "b" * 3900 + "JOB_KEPT" + "b" * 5000 + "JOB_CUT"

    prompt = build_analyze_resume_prompt(resume, job)

    assert "RESUME_KEPT" in prompt
    assert "RESUME_CUT" not in prompt
    assert "JOB_KEPT" in prompt
    assert "JOB_CUT" not in prompt


# ── Job comparison ──────────────────────────────────────────────────────────

def test_compare_prompt_includes_the_job_description():
    """Scoring compatibility from a job title alone produces a hollow number."""
    from modules.ai.infrastructure.llm_providers.prompt_builder import build_compare_job_prompt

    prompt = build_compare_job_prompt(
        "CV",
        {
            "title": "Backend",
            "company": "Acme",
            "description": "DESCRICAO DETALHADA",
            "requirements": ["python"],
            "skills": ["docker"],
        },
    )
    assert "DESCRICAO DETALHADA" in prompt
    assert "python" in prompt
    assert "docker" in prompt
    assert "compatibility_score" in prompt


def test_compare_prompt_tolerates_a_sparse_job():
    from modules.ai.infrastructure.llm_providers.prompt_builder import build_compare_job_prompt

    prompt = build_compare_job_prompt("CV", {})
    assert "the position" in prompt
    assert "the company" in prompt


# ── Tailored resume ─────────────────────────────────────────────────────────

def test_tailored_resume_prompt_forbids_invention():
    from modules.ai.infrastructure.llm_providers.prompt_builder import build_tailored_resume_prompt

    prompt = build_tailored_resume_prompt("CV", {"title": "SRE", "requirements": ["linux"]})
    assert "Never invent anything" in prompt
    assert "linux" in prompt


# ── Career Q&A ──────────────────────────────────────────────────────────────

def test_answer_prompt_includes_context_only_when_present():
    from modules.ai.infrastructure.llm_providers.prompt_builder import build_career_answer_prompt

    with_context = build_career_answer_prompt("Como negociar?", "Sênior, 8 anos")
    assert "Sênior, 8 anos" in with_context

    without_context = build_career_answer_prompt("Como negociar?")
    assert "Context about the candidate" not in without_context


# ── Profile suggestions ─────────────────────────────────────────────────────

def test_profile_prompt_is_anchored_to_the_resume():
    from modules.ai.infrastructure.llm_providers.prompt_builder import (
        build_profile_suggestions_prompt,
    )

    prompt = build_profile_suggestions_prompt("MEU CURRICULO", "Staff Engineer")
    assert "MEU CURRICULO" in prompt
    assert "Staff Engineer" in prompt
    assert "Never invent employers, titles or dates" in prompt


def test_profile_prompt_omits_an_empty_target_role():
    from modules.ai.infrastructure.llm_providers.prompt_builder import (
        build_profile_suggestions_prompt,
    )

    assert "Target role" not in build_profile_suggestions_prompt("CV")
