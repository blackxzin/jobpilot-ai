"""Offline LLM provider — runs every AI feature with no API key and no network.

Why this exists: without it, a fresh clone of JobPilot is a dead app. Matching,
ATS scoring, cover letters, tailored resumes and chat all raise 502 until the
user has signed up for a provider, so nobody can see what the product does
before committing a credit card. This provider is the default fallback and
powers demo mode.

It is deliberately not a fake: scores come from real lexical overlap between
the resume and the job posting, and generated text is composed from the actual
resume and job data. The output is weaker and more formulaic than a real LLM's
-- which is the honest trade -- but it is never invented.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import AsyncGenerator

from modules.ai.domain.llm_provider import LLMProvider

# Words carrying no signal for skill matching, in the two languages the app
# targets. Kept short on purpose: an over-eager stoplist drops real skills.
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "in", "is", "it", "its", "of", "on", "or", "that", "the", "to", "was", "were",
    "will", "with", "you", "your", "our", "we", "they", "this", "these", "those",
    "e", "o", "os", "um", "uma", "de", "da", "do", "das", "dos", "em", "no",
    "na", "nos", "nas", "por", "para", "com", "sem", "que", "se", "ao", "aos",
    "sua", "seu", "suas", "seus", "mais", "como", "ser", "ter", "sobre", "entre",
    "voce", "nosso", "nossa", "sao", "foi", "eh", "pelo", "pela",
}

# Terms that behave like skills when they appear in either document. Matching
# on a curated list rather than raw token overlap keeps the "matched skills"
# output readable instead of a wall of common nouns.
_SKILL_TERMS = {
    "python", "javascript", "typescript", "java", "kotlin", "swift", "go", "rust",
    "ruby", "php", "csharp", "c++", "scala", "elixir", "dart", "sql", "nosql",
    "react", "nextjs", "next.js", "vue", "angular", "svelte", "node", "nodejs",
    "django", "flask", "fastapi", "spring", "rails", "laravel", "express",
    "postgres", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "kafka", "rabbitmq", "celery", "graphql", "rest", "grpc", "microservices",
    "docker", "kubernetes", "terraform", "ansible", "aws", "gcp", "azure",
    "linux", "git", "github", "gitlab", "jenkins", "cicd", "devops", "observability",
    "pytest", "jest", "vitest", "cypress", "playwright", "tdd", "bdd",
    "pandas", "numpy", "pytorch", "tensorflow", "sklearn", "spark", "airflow",
    "machine", "learning", "data", "backend", "frontend", "fullstack", "mobile",
    "android", "ios", "flutter", "react-native", "tailwind", "css", "html",
    "agile", "scrum", "kanban", "jira", "figma", "ux", "ui", "api", "sre",
    "seguranca", "security", "oauth", "jwt", "lgpd", "gdpr", "etl", "bi",
    "ingles", "english", "espanhol", "spanish", "remoto", "remote", "hibrido",
    "senior", "pleno", "junior", "estagio", "clt", "pj", "lideranca", "mentoria",
}


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


# Internal punctuation is meaningful in technology names ("next.js", "c++",
# "react-native"), but trailing punctuation is just the end of a sentence.
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+#._-]*")
_TRAILING_PUNCTUATION = "._-"


def tokenize(text: str) -> list[str]:
    """Lowercase, de-accent and split text into comparable word tokens."""
    cleaned = _strip_accents((text or "").lower())
    tokens = (t.rstrip(_TRAILING_PUNCTUATION) for t in _TOKEN_RE.findall(cleaned))
    return [t for t in tokens if t and t not in _STOPWORDS]


def extract_skills(text: str) -> set[str]:
    """Return the known skill terms present in a document."""
    return {t for t in tokenize(text) if t in _SKILL_TERMS}


def _job_text(job: dict) -> str:
    parts = [
        job.get("title") or "",
        job.get("company") or "",
        job.get("description") or "",
        " ".join(job.get("requirements") or []),
        " ".join(job.get("skills") or []),
    ]
    return " ".join(parts)


def score_match(resume: str, job_text: str) -> tuple[int, set[str], set[str]]:
    """Score resume/job fit from skill overlap.

    Returns (score 0-100, matched skills, missing skills). The score is the
    share of the job's skills the resume covers, floored at 20 so an empty
    job posting does not read as an outright rejection.
    """
    resume_skills = extract_skills(resume)
    job_skills = extract_skills(job_text)

    if not job_skills:
        # Nothing to match against: fall back to generic token overlap so the
        # number still reflects the two documents rather than a constant.
        resume_tokens, job_tokens = set(tokenize(resume)), set(tokenize(job_text))
        if not job_tokens:
            return 50, set(), set()
        overlap = len(resume_tokens & job_tokens) / len(job_tokens)
        return max(20, min(95, round(overlap * 100))), set(), set()

    matched = resume_skills & job_skills
    missing = job_skills - resume_skills
    coverage = len(matched) / len(job_skills)
    return max(20, min(98, round(coverage * 100))), matched, missing


# Weights for the standalone resume audit. They sum to 100 and are ordered by
# how much each factor actually affects an ATS parse.
_AUDIT_WEIGHTS = {
    "skills": 30,      # recognisable technology terms at all
    "length": 20,      # enough substance to parse
    "quantified": 20,  # numbers, the single strongest signal to a human reader
    "contact": 15,     # an email an ATS can extract
    "sections": 15,    # recognisable headings
}

_SECTION_HINTS = (
    "experiencia", "experience", "formacao", "education", "competencias", "skills",
    "resumo", "summary", "projetos", "projects", "certificacoes", "idiomas",
)

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def audit_resume(resume: str) -> tuple[int, list[str], list[str]]:
    """Score a resume on its own terms: is it parseable and substantial?

    Returns (score 0-100, strengths, suggestions).

    Scoring a lone resume by overlap with a generic role profile is misleading
    — nobody matches every technology in the industry, so even excellent CVs
    land near zero. What a standalone ATS check can honestly measure is
    whether the document survives automated parsing.
    """
    text = resume or ""
    normalized = _strip_accents(text.lower())
    skills = extract_skills(text)

    score = 0
    strengths: list[str] = []
    suggestions: list[str] = []

    # Skills — saturates at 8 recognised terms.
    skill_ratio = min(len(skills) / 8, 1.0)
    score += round(_AUDIT_WEIGHTS["skills"] * skill_ratio)
    if len(skills) >= 5:
        strengths.append(f"{len(skills)} competências técnicas reconhecíveis")
    else:
        suggestions.append(
            "Adicione uma seção de competências com as tecnologias que você domina — "
            "é o que um ATS procura primeiro."
        )

    # Length — under ~150 words there is nothing to rank.
    words = len(normalized.split())
    length_ratio = min(words / 350, 1.0)
    score += round(_AUDIT_WEIGHTS["length"] * length_ratio)
    if words < 150:
        suggestions.append(
            "Currículo curto para leitura automatizada: descreva responsabilidades "
            "e resultados de cada experiência."
        )
    else:
        strengths.append("Extensão adequada para leitura automatizada")

    # Quantified results.
    numbers = len(re.findall(r"\d+\s*%|\d[\d.,]*\s*(?:mil|milhoes|x|ms|k)\b|\b\d{2,}\b", normalized))
    if numbers >= 3:
        score += _AUDIT_WEIGHTS["quantified"]
        strengths.append("Resultados quantificados com números")
    elif numbers >= 1:
        score += _AUDIT_WEIGHTS["quantified"] // 2
        suggestions.append("Quantifique mais resultados (ex.: 'reduzi a latência em 40%').")
    else:
        suggestions.append(
            "Nenhum resultado numérico encontrado. Números são o sinal mais forte "
            "para quem lê o currículo (ex.: 'cobertura de testes de 22% para 84%')."
        )

    # Contact details.
    if _EMAIL_RE.search(text):
        score += _AUDIT_WEIGHTS["contact"]
        strengths.append("Contato extraível pelo ATS")
    else:
        suggestions.append("Inclua um e-mail em texto (não em imagem) no topo do currículo.")

    # Recognisable sections.
    found_sections = sum(1 for hint in _SECTION_HINTS if hint in normalized)
    if found_sections >= 3:
        score += _AUDIT_WEIGHTS["sections"]
        strengths.append("Seções bem delimitadas")
    elif found_sections >= 1:
        score += _AUDIT_WEIGHTS["sections"] // 2
        suggestions.append("Use títulos de seção explícitos: Resumo, Experiência, Formação, Competências.")
    else:
        suggestions.append("Sem seções reconhecíveis. Um ATS precisa de títulos como 'Experiência' e 'Formação'.")

    return min(score, 100), strengths, suggestions


def _bullets(items, empty: str) -> str:
    listed = [i for i in items if i]
    if not listed:
        return f"- {empty}"
    return "\n".join(f"- {item}" for item in listed)


class OfflineProvider(LLMProvider):
    """Deterministic, network-free implementation of the LLM provider port."""

    def __init__(self, api_key: str | None = None, model: str = "offline-analyzer", base_url: str | None = None):
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return "offline"

    async def generate(self, prompt: str, **kwargs) -> str:
        return (
            "Modo offline ativo — nenhum provedor de IA está configurado.\n\n"
            "As análises de compatibilidade, ATS, carta de apresentação e currículo "
            "personalizado continuam funcionando com o analisador local. Para respostas "
            "geradas por um modelo de linguagem, configure uma chave em Configurações → IA."
        )

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        yield await self.generate(prompt, **kwargs)

    async def summarize(self, text: str, **kwargs) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", (text or "").strip())
        return " ".join(sentences[:3]) or "Sem conteúdo para resumir."

    async def analyze_resume(self, resume: str, job_description: str, **kwargs) -> dict:
        if not (job_description or "").strip():
            # No target job: audit the document itself rather than comparing it
            # to nothing, which would score every resume identically.
            score, strengths, suggestions = audit_resume(resume)
            return {
                "score": score,
                "matched_skills": sorted(extract_skills(resume)),
                "missing_skills": [],
                "suggestions": suggestions,
                "strengths": strengths,
                "provider": "offline",
            }

        score, matched, missing = score_match(resume, job_description)
        suggestions = [
            f"Inclua '{skill}' no currículo se você tiver essa experiência — a vaga cita explicitamente."
            for skill in sorted(missing)[:5]
        ]
        if len(resume or "") < 800:
            suggestions.append("Currículo curto para leitura de ATS: descreva resultados de cada experiência.")
        if not re.search(r"\d", resume or ""):
            suggestions.append("Adicione números aos resultados (ex.: 'reduzi o tempo de build em 40%').")
        return {
            "score": score,
            "matched_skills": sorted(matched),
            "missing_skills": sorted(missing),
            "suggestions": suggestions or ["Currículo bem alinhado à vaga — mantenha o formato."],
            "strengths": [f"Domínio comprovado de {s}" for s in sorted(matched)[:5]]
            or ["Experiência descrita de forma clara"],
            "provider": "offline",
        }

    async def compare_job(self, resume: str, job: dict, **kwargs) -> dict:
        score, matched, missing = score_match(resume, _job_text(job))
        reasons = [{"text": f"Você já trabalha com {s}", "type": "match"} for s in sorted(matched)[:6]]
        reasons += [{"text": f"A vaga pede {s} e não achei no currículo", "type": "gap"} for s in sorted(missing)[:6]]
        return {
            "compatibility_score": score,
            "match_reasons": reasons or [{"text": "Sem sinais fortes nos dois documentos", "type": "gap"}],
            "suggestions": [
                f"Cite projetos concretos usando {s} na carta de apresentação." for s in sorted(missing)[:3]
            ]
            or ["Perfil aderente: destaque resultados mensuráveis na candidatura."],
            "provider": "offline",
        }

    async def generate_cover_letter(
        self, resume: str, job: dict, language: str = "pt-BR", tone: str = "professional", **kwargs
    ) -> str:
        title = job.get("title") or "a vaga"
        company = job.get("company") or "a empresa"
        _, matched, missing = score_match(resume, _job_text(job))
        highlights = sorted(matched)[:5]
        skills_line = ", ".join(highlights) if highlights else "minha experiência prática"

        return (
            f"Prezada equipe de {company},\n\n"
            f"Escrevo para me candidatar à posição de {title}. "
            f"Ao longo da minha trajetória venho trabalhando diretamente com {skills_line}, "
            f"exatamente o conjunto de competências que vocês descrevem na vaga.\n\n"
            f"No meu histórico recente atuei em entregas que exigiram {skills_line}, "
            "sempre com foco em resultado mensurável e em colaboração próxima com produto e design. "
            "Gosto de assumir problemas de ponta a ponta: entender o contexto, propor a solução mais "
            "simples que resolve, e acompanhar o impacto depois de entregue.\n\n"
            f"Tenho interesse específico em {company} pelo tipo de problema descrito na vaga, e acredito "
            "que consigo contribuir desde as primeiras semanas. Ficaria feliz em detalhar qualquer um "
            "desses pontos em uma conversa.\n\n"
            "Atenciosamente,\n\n"
            "---\n"
            "_Carta montada pelo analisador local do JobPilot (modo offline). "
            "Configure um provedor de IA em Configurações → IA para uma carta gerada por LLM._"
        )

    async def generate_tailored_resume(self, resume: str, job: dict, **kwargs) -> str:
        title = job.get("title") or "a vaga"
        company = job.get("company") or "a empresa"
        _, matched, missing = score_match(resume, _job_text(job))

        return (
            f"# Currículo direcionado — {title} @ {company}\n\n"
            "## Resumo profissional\n"
            f"Profissional com experiência prática em {', '.join(sorted(matched)[:6]) or 'desenvolvimento de software'}, "
            f"buscando a posição de {title}.\n\n"
            "## Competências priorizadas para esta vaga\n"
            f"{_bullets(sorted(matched), 'Nenhuma competência da vaga encontrada no currículo')}\n\n"
            "## Lacunas a endereçar\n"
            f"{_bullets(sorted(missing), 'Nenhuma lacuna relevante identificada')}\n\n"
            "## Currículo original\n"
            f"{(resume or '').strip() or '_Currículo sem texto extraído._'}\n\n"
            "---\n"
            "_Reordenado pelo analisador local (modo offline). Configure um provedor de IA "
            "em Configurações → IA para uma reescrita completa por LLM._"
        )

    async def answer_question(self, question: str, context: str = "", **kwargs) -> str:
        return (
            "O chat de carreira precisa de um provedor de IA configurado para responder de verdade.\n\n"
            "Vá em **Configurações → IA** e adicione uma chave (OpenAI, Anthropic, Gemini, "
            "NVIDIA NIM, OpenRouter) ou aponte para um Ollama local.\n\n"
            "Enquanto isso, tudo que não depende de geração de texto livre continua funcionando: "
            "matching, ATS Score, carta de apresentação e currículo direcionado usam o analisador local."
        )

    async def health_check(self) -> bool:
        return True
