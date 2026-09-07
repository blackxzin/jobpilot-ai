"""Shared prompt builders for LLM providers.

Every provider generated its own copy of the cover-letter prompt, so adding a
feature (language, tone) meant editing six near-identical strings. Centralizing
it here keeps the six providers as thin adapters instead of prompt duplicates.
"""
from __future__ import annotations

_TONE_INSTRUCTIONS = {
    "professional": "Professional but warm.",
    "formal": "Formal and reserved, no casual language.",
    "enthusiastic": "Enthusiastic and energetic, while staying credible.",
    "casual": "Casual and conversational, while staying respectful.",
}

_LANGUAGE_NAMES = {
    "pt-BR": "Brazilian Portuguese",
    "en": "English",
    "es": "Spanish",
}


def build_cover_letter_prompt(resume: str, job: dict, language: str = "pt-BR", tone: str = "professional") -> str:
    """Build the cover-letter generation prompt shared by every LLM provider."""
    company = job.get("company") or "the company"
    job_title = job.get("title") or "the position"
    job_desc = (job.get("description") or "")[:800]
    requirements = job.get("requirements") or []
    skills = job.get("skills") or []
    tone_instruction = _TONE_INSTRUCTIONS.get(tone, _TONE_INSTRUCTIONS["professional"])
    language_name = _LANGUAGE_NAMES.get(language, language)

    keyword_line = ""
    if requirements or skills:
        keywords = ", ".join([*requirements, *skills])
        keyword_line = f"Key requirements/skills to weave in naturally, using the job's own wording where truthful: {keywords}\n"

    return f"""Write a personalized cover letter for a job application.

Candidate's resume:
{resume}

Applying for: {job_title} at {company}
{keyword_line}Job description: {job_desc}

The cover letter must:
- Be written in {language_name}
- Be 3-4 paragraphs, max 400 words
- Reference specific relevant experience from the resume
- Show genuine, specific interest in {company} (not generic filler)
- Weave in the matching requirements/skills above, to help with ATS keyword matching
- Never invent experience that is not in the resume
- Tone: {tone_instruction}"""


def build_analyze_resume_prompt(resume: str, job_description: str) -> str:
    """Build the ATS-analysis prompt shared by every LLM provider."""
    return f"""You are an ATS (Applicant Tracking System) analyst.
Compare the resume against the job description and score it the way an ATS would.

RESUME:
{resume[:6000]}

JOB DESCRIPTION:
{job_description[:4000]}

Return ONLY a JSON object with exactly these keys:
- "score": integer 0-100, how well the resume passes ATS screening for this job
- "matched_skills": array of skills present in both the resume and the job
- "missing_skills": array of skills the job asks for that the resume lacks
- "suggestions": array of concrete, actionable rewrite suggestions (in Portuguese)
- "strengths": array of the resume's strongest points for this job (in Portuguese)

No prose outside the JSON."""


def build_compare_job_prompt(resume: str, job: dict) -> str:
    """Build the resume/job compatibility prompt shared by every LLM provider.

    The job description and requirements are included: scoring compatibility
    from a job title alone produces a number with nothing behind it.
    """
    title = job.get("title") or "the position"
    company = job.get("company") or "the company"
    description = (job.get("description") or "")[:2500]
    requirements = job.get("requirements") or []
    skills = job.get("skills") or []

    detail = ""
    if requirements:
        detail += f"\nREQUIREMENTS: {', '.join(requirements)}"
    if skills:
        detail += f"\nSKILLS WANTED: {', '.join(skills)}"

    return f"""Assess how well this candidate fits this job.

RESUME:
{resume[:6000]}

JOB: {title} at {company}{detail}
DESCRIPTION:
{description}

Return ONLY a JSON object with exactly these keys:
- "compatibility_score": integer 0-100
- "match_reasons": array of objects {{"text": "...", "type": "match"|"gap"}} (text in Portuguese)
- "suggestions": array of strings, how the candidate could close the gaps (in Portuguese)

No prose outside the JSON."""


def build_tailored_resume_prompt(resume: str, job: dict) -> str:
    """Build the resume-tailoring prompt shared by every LLM provider."""
    title = job.get("title") or "the position"
    company = job.get("company") or "the company"
    description = (job.get("description") or "")[:1500]
    keywords = ", ".join([*(job.get("requirements") or []), *(job.get("skills") or [])])
    keyword_line = f"\nATS keywords to include where truthful: {keywords}" if keywords else ""

    return f"""Rewrite this resume so it targets the job below. Return ONLY the rewritten resume in Markdown.

ORIGINAL RESUME:
{resume[:6000]}

TARGET: {title} at {company}{keyword_line}
JOB DESCRIPTION:
{description}

Rules:
- Keep every real experience, employer and date. Never invent anything.
- Rewrite bullet points to foreground what matters for this job.
- Open with a professional summary aimed at this role.
- Include a skills section ordered by relevance to the job.
- Write in the same language as the original resume."""


def build_career_answer_prompt(question: str, context: str = "") -> str:
    """Build the career Q&A prompt shared by every LLM provider."""
    context_line = f"Context about the candidate:\n{context}\n\n" if context else ""
    return (
        "You are a practical, direct career coach for JobPilot AI. "
        "Answer in the same language as the question.\n\n"
        f"{context_line}Question: {question}"
    )


def build_profile_suggestions_prompt(resume: str, target_role: str = "") -> str:
    """Build the LinkedIn-positioning prompt shared by every LLM provider.

    Grounded in the candidate's own resume. The previous version asked the
    model to infer a person's profile from nothing but a LinkedIn URL, which
    produced confident, entirely invented biographies.
    """
    target_line = f"\nTarget role the candidate is aiming for: {target_role}" if target_role else ""

    return f"""You are a career strategist reviewing a candidate's resume to improve how they
present themselves on LinkedIn.

RESUME:
{resume[:6000]}{target_line}

Return ONLY a JSON object with exactly these keys:
- "headline": a LinkedIn headline of at most 120 characters, in the resume's language
- "about": a 3-4 sentence LinkedIn "About" section, first person, in the resume's language
- "skills": array of skills to list, ordered by how strongly the resume evidences them
- "suggested_roles": array of job titles this experience actually supports
- "experience_years": integer, years of professional experience the resume shows
- "gaps": array of things missing from the resume that would strengthen the profile
- "analysis": two or three sentences of positioning advice, in the resume's language

Every claim must be supported by the resume. Never invent employers, titles or dates.
No prose outside the JSON."""
