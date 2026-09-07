"""Demo data seeding.

Purpose: let anyone run `docker compose up` with no API keys, no job-board
access and no manual data entry, log in, and see every screen populated —
dashboard KPIs, a job board, a pipeline with real statuses, interviews on the
calendar, cover letters, notifications and working semantic search.

Seeding is idempotent: it checks for the demo user and returns early, so
restarting the stack does not duplicate anything.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from core.config import settings
from core.database import get_session_factory
from core.logger import get_logger
from core.models import (
    ApplicationModel,
    CalendarEventModel,
    CompanyModel,
    CoverLetterModel,
    JobEmbeddingModel,
    JobModel,
    JobRequirementModel,
    NotificationModel,
    ResumeModel,
    SkillModel,
    UserModel,
)
from core.security import hash_password

logger = get_logger(__name__)

DEMO_RESUME = """Lucas Oliveira — Engenheiro de Software Backend
São Paulo, SP · Remoto · lucas.demo@jobpilot.ai

RESUMO
Engenheiro backend com 6 anos de experiência construindo APIs e sistemas
distribuídos em Python. Foco em FastAPI, PostgreSQL e infraestrutura em AWS.
Experiência liderando squads pequenos e mentorando pessoas desenvolvedoras.

EXPERIÊNCIA

Tech Lead Backend — Nuvem Pagamentos (2023 - atual)
- Reescrevi o serviço de liquidação em FastAPI, reduzindo a latência p95 de
  820ms para 140ms.
- Migrei o processamento assíncrono para Celery + Redis, absorvendo picos de
  12x no Black Friday sem degradação.
- Implementei observabilidade com métricas e tracing; MTTR caiu de 45 para 8 minutos.

Desenvolvedor Backend Sênior — Loja Verde (2021 - 2023)
- Construí a API de catálogo em Django REST atendendo 4 milhões de requisições/dia.
- Otimizei consultas PostgreSQL com índices parciais, cortando 60% do custo de banco.
- Introduzi testes com pytest, elevando a cobertura de 22% para 84%.

Desenvolvedor Backend — Agência Kernel (2019 - 2021)
- Entreguei integrações REST e GraphQL para clientes de e-commerce.
- Containerizei o parque de aplicações com Docker, padronizando os deploys.

FORMAÇÃO
Bacharelado em Ciência da Computação — Universidade Federal (2019)

COMPETÊNCIAS
Python, FastAPI, Django, PostgreSQL, Redis, Celery, Docker, Kubernetes, AWS,
Terraform, pytest, Git, CI/CD, REST, GraphQL, observabilidade, mentoria

IDIOMAS
Português (nativo), Inglês (avançado)
"""

DEMO_SKILLS = [
    ("Python", "language", "expert"),
    ("FastAPI", "framework", "expert"),
    ("PostgreSQL", "database", "advanced"),
    ("Docker", "devops", "advanced"),
    ("AWS", "cloud", "advanced"),
    ("Celery", "framework", "advanced"),
    ("Kubernetes", "devops", "intermediate"),
    ("Terraform", "devops", "intermediate"),
]

# (company, title, location, remote, seniority, description, requirements, salary)
DEMO_JOBS = [
    (
        "Nubank",
        "Engenheiro(a) de Software Backend Sênior",
        "São Paulo, SP",
        True,
        "senior",
        "Procuramos pessoa engenheira backend para atuar no core bancário. "
        "Stack em Python e Kotlin, PostgreSQL, Kafka e AWS. Você vai desenhar "
        "serviços de alta disponibilidade, participar de on-call e mentorar o time.",
        ["Python", "PostgreSQL", "AWS", "Kafka", "microservices", "inglês"],
        (18000, 26000),
    ),
    (
        "Stone",
        "Desenvolvedor(a) Python Pleno",
        "Rio de Janeiro, RJ",
        True,
        "pleno",
        "Time de pagamentos buscando pessoa desenvolvedora Python para evoluir "
        "APIs de conciliação. Trabalhamos com FastAPI, Celery, Redis e Docker, "
        "com deploy contínuo em Kubernetes.",
        ["Python", "FastAPI", "Celery", "Redis", "Docker", "Kubernetes"],
        (12000, 17000),
    ),
    (
        "iFood",
        "Tech Lead Backend",
        "Campinas, SP",
        False,
        "senior",
        "Liderança técnica de uma squad de logística. Esperamos experiência com "
        "sistemas distribuídos, observabilidade e mentoria. Stack Python/Go, "
        "PostgreSQL, Terraform e AWS.",
        ["Python", "Go", "Terraform", "AWS", "observabilidade", "liderança"],
        (25000, 34000),
    ),
    (
        "Loft",
        "Engenheiro(a) de Dados",
        "São Paulo, SP",
        True,
        "pleno",
        "Construção de pipelines de dados com Airflow e Spark, modelagem "
        "analítica em PostgreSQL e entregas para times de produto.",
        ["Python", "Airflow", "Spark", "SQL", "ETL"],
        (14000, 20000),
    ),
    (
        "Hotmart",
        "Pessoa Desenvolvedora Full Stack",
        "Belo Horizonte, MG",
        True,
        "pleno",
        "Frente de checkout: React e TypeScript no frontend, Python no backend. "
        "Cultura de testes automatizados e revisão de código.",
        ["React", "TypeScript", "Python", "REST", "testes"],
        (11000, 16000),
    ),
    (
        "QuintoAndar",
        "Engenheiro(a) de Plataforma",
        "São Paulo, SP",
        True,
        "senior",
        "Time de plataforma responsável por Kubernetes, CI/CD e ferramentas "
        "internas. Buscamos alguém com forte base em Linux, Terraform e Go.",
        ["Kubernetes", "Terraform", "Go", "Linux", "CI/CD", "observabilidade"],
        (20000, 28000),
    ),
    (
        "Mercado Livre",
        "Backend Developer (Python)",
        "Remoto",
        True,
        "pleno",
        "Desenvolvimento de APIs REST de alto tráfego. Python, Django, "
        "PostgreSQL e Redis. Ambiente remoto com times distribuídos na América Latina.",
        ["Python", "Django", "PostgreSQL", "Redis", "REST", "espanhol"],
        (13000, 19000),
    ),
    (
        "PicPay",
        "Estágio em Desenvolvimento Backend",
        "São Paulo, SP",
        True,
        "estagio",
        "Programa de estágio com trilha de backend em Python. Ideal para quem "
        "está em formação e quer aprender boas práticas de engenharia.",
        ["Python", "Git", "SQL"],
        (2500, 3200),
    ),
]

# (job index, status, days ago)
DEMO_APPLICATIONS = [
    (0, "technical_interview", 21),
    (1, "hr_interview", 17),
    (2, "offer", 30),
    (3, "rejected", 26),
    (4, "under_review", 9),
    (5, "applied", 5),
    (6, "rejected", 14),
]

DEMO_EVENTS = [
    ("Entrevista técnica — Nubank", "interview", 2, "Foco em sistemas distribuídos e Python."),
    ("Conversa com RH — Stone", "interview", 4, "Alinhamento de expectativas e faixa salarial."),
    ("Prazo de resposta — iFood", "deadline", 6, "Responder à proposta até esta data."),
    ("Follow-up — Hotmart", "reminder", 9, "Enviar e-mail de acompanhamento."),
]

DEMO_NOTIFICATIONS = [
    ("Entrevista confirmada", "A Nubank confirmou sua entrevista técnica para esta semana.", "read"),
    ("Nova vaga compatível", "Encontramos 3 vagas com mais de 70% de compatibilidade com seu currículo.", "sent"),
    ("Proposta recebida", "A iFood enviou uma proposta. Confira os detalhes na sua pipeline.", "sent"),
    ("Currículo analisado", "Seu ATS Score foi atualizado após a última revisão do currículo.", "sent"),
]


async def seed_demo_data() -> bool:
    """Create the demo account and its data. Returns True when it seeded.

    Safe to call on every startup: an existing demo user short-circuits it.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        existing = (
            await session.execute(
                select(UserModel).where(UserModel.email == settings.DEMO_EMAIL)
            )
        ).scalar_one_or_none()
        if existing is not None:
            logger.info("demo_seed_skipped", reason="already_seeded")
            return False

        now = datetime.now(UTC)
        user = UserModel(
            email=settings.DEMO_EMAIL,
            hashed_password=hash_password(settings.DEMO_PASSWORD),
            full_name="Lucas Oliveira (Demo)",
            is_active=True,
        )
        session.add(user)
        await session.flush()

        resume = ResumeModel(
            user_id=user.id,
            title="Currículo — Backend Sênior",
            content_text=DEMO_RESUME,
            file_url="demo/curriculo-backend.pdf",
            ats_score=78,
            ats_breakdown={
                "matched_skills": ["python", "postgresql", "docker", "aws", "celery"],
                "missing_skills": ["kafka", "go"],
                "suggestions": [
                    "Cite experiência com Kafka se houver — várias vagas do seu perfil pedem.",
                    "Adicione uma linha sobre liderança técnica no resumo do topo.",
                ],
                "strengths": ["Resultados quantificados", "Stack coerente com as vagas-alvo"],
            },
        )
        session.add(resume)
        await session.flush()

        for name, category, level in DEMO_SKILLS:
            session.add(
                SkillModel(resume_id=resume.id, name=name, category=category, level=level)
            )

        jobs = await _seed_jobs(session, now)
        await _seed_applications(session, user, resume, jobs, now)
        await _seed_calendar(session, user, now)
        await _seed_notifications(session, user, now)
        await _seed_cover_letter(session, user, jobs[0], now)

        await session.commit()

    logger.info("demo_seed_completed", email=settings.DEMO_EMAIL, jobs=len(DEMO_JOBS))
    return True


async def _seed_jobs(session, now: datetime) -> list[JobModel]:
    """Insert the demo job board and index every posting for semantic search."""
    from modules.search.infrastructure import EmbeddingService

    embedder = EmbeddingService()
    jobs: list[JobModel] = []

    for index, (
        company_name,
        title,
        location,
        is_remote,
        seniority,
        description,
        requirements,
        salary,
    ) in enumerate(DEMO_JOBS):
        company = CompanyModel(name=company_name, location=location)
        session.add(company)
        await session.flush()

        job = JobModel(
            source="demo",
            source_id=f"demo-{index}",
            title=title,
            company_id=company.id,
            description=description,
            seniority=seniority,
            location=location,
            location_type="remote" if is_remote else "onsite",
            is_remote=is_remote,
            salary_min=float(salary[0]),
            salary_max=float(salary[1]),
            currency="BRL",
            apply_url="https://example.com/vagas/demo",
            posted_at=now - timedelta(days=index * 2),
        )
        session.add(job)
        await session.flush()

        for requirement in requirements:
            session.add(
                JobRequirementModel(
                    job_id=job.id,
                    requirement=requirement,
                    category="skill",
                    is_must_have=True,
                )
            )

        text = f"{title} {company_name} {location} {description} {' '.join(requirements)}"
        session.add(
            JobEmbeddingModel(
                job_id=job.id,
                embedding=await embedder.embed_text(text),
                chunk_text=text[:500],
            )
        )
        jobs.append(job)

    return jobs


async def _seed_applications(session, user, resume, jobs, now: datetime) -> None:
    for job_index, status, days_ago in DEMO_APPLICATIONS:
        applied_at = now - timedelta(days=days_ago)
        session.add(
            ApplicationModel(
                job_id=jobs[job_index].id,
                resume_id=resume.id,
                user_id=user.id,
                status=status,
                custom_message="Candidatura registrada no modo demonstração.",
                source_platform="demo",
                applied_at=applied_at,
                created_at=applied_at,
                responded_at=None if status == "applied" else applied_at + timedelta(days=3),
            )
        )


async def _seed_calendar(session, user, now: datetime) -> None:
    for title, event_type, days_ahead, notes in DEMO_EVENTS:
        session.add(
            CalendarEventModel(
                user_id=user.id,
                title=title,
                event_type=event_type,
                date=now + timedelta(days=days_ahead),
                notes=notes,
                status="scheduled",
            )
        )


async def _seed_notifications(session, user, now: datetime) -> None:
    for index, (title, message, status) in enumerate(DEMO_NOTIFICATIONS):
        session.add(
            NotificationModel(
                user_id=user.id,
                type="email",
                channel="email",
                title=title,
                message=message,
                status=status,
                read_at=now - timedelta(days=index) if status == "read" else None,
                created_at=now - timedelta(days=index),
            )
        )


async def _seed_cover_letter(session, user, job, now: datetime) -> None:
    from modules.ai.infrastructure.llm_providers.offline_provider import OfflineProvider

    content = await OfflineProvider().generate_cover_letter(
        DEMO_RESUME,
        {"title": job.title, "company": "Nubank", "description": job.description},
    )
    session.add(
        CoverLetterModel(
            user_id=user.id,
            job_id=job.id,
            title=f"{job.title} — Nubank",
            content=content,
            created_at=now - timedelta(days=20),
        )
    )
