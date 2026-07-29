# JobPilot AI — Plano de Arquitetura e Roadmap

> **Status:** Análise de Requisitos | **Versão:** 0.1 — Aguardando Aprovação

---

## 1. Análise Completa dos Requisitos

### 1.1 Requisitos Funcionais Resumidos

| ID | Funcionalidade | Prioridade |
|----|---------------|------------|
| RF-01 | Dashboard com métricas de carreira | P0 |
| RF-02 | Perfil completo (experiências, skills, portfólio) | P0 |
| RF-03 | Importação inteligente (PDF, LinkedIn, GitHub) | P0 |
| RF-04 | Buscador de vagas multi-plataforma | P0 |
| RF-05 | Matching inteligente com score | P0 |
| RF-06 | ATS Score para currículo | P1 |
| RF-07 | Currículo inteligente personalizado por vaga | P1 |
| RF-08 | Geração de carta de apresentação | P1 |
| RF-09 | Chat assistente IA | P1 |
| RF-10 | Automação de candidaturas (quando permitido) | P2 |
| RF-11 | Rastreamento de status de candidatura | P0 |
| RF-12 | Agenda de entrevistas e lembretes | P2 |
| RF-13 | Notificações multi-canal | P2 |
| RF-14 | Analytics de carreira | P1 |
| RF-15 | Abstração multi-provedor LLM | P0 |
| RF-16 | Configuração de API keys por usuário | P0 |

### 1.2 Requisitos Não-Funcionais

- **Performance**: P95 < 500ms para leitura, < 2s para operações de IA
- **Disponibilidade**: 99.5% target para MVP
- **Segurança**: Criptografia de API keys em repouso, HTTPS obrigatório
- **Escalabilidade**: Suporte a 10.000 usuários simultâneos no MVP
- **Observabilidade**: Logs estruturados (JSON), métricas, tracing distribuído
- **Testes**: Cobertura mínima 80% no backend, 70% no frontend

### 1.3 Restrições Legais e Éticas Críticas

**⚠️ Esta é a primeira decisão que questiono:**

O escopo original inclui scraping de LinkedIn, Indeed, Glassdoor, etc. Preciso alertar:

| Plataforma | API Oficial | Status da API | Risco de Scraping |
|-----------|-------------|---------------|-------------------|
| LinkedIn | Sim (Limited API) | Restrita, paga a partir de determinado tier | ❌ **Alto** — ToS proíbe explicitamente |
| Gupy | Sim | Acessível com registro | 🟡 Baixo-Médio |
| Indeed | Sim (Partner API paga) | Paga | 🟢 Baixo (se usar API) |
| Glassdoor | Sim (Partner API) | Paga | 🟢 Baixo (se usar API) |
| RemoteOK | Não | — | 🟢 Baixo (HTML público) |
| WeWorkRemotely | Não | — | 🟢 Baixo |

**Minha recomendação:**
1. Priorizar integrações via API oficial primeiro (Gupy, Indeed, Glassdoor API, LinkedIn API)
2. Para plataformas sem API, rastrear RSS feeds públicos onde disponíveis
3. **Remover scraping de LinkedIn do escopo inicial** — o risco legal e técnico é alto (CAPTCHAs, bloqueios IP, ToS violations)
4. Documentar claramente que o respeito aos ToS é uma decisão de design, não uma limitação técnica

---

## 2. Arquitetura Ideal

### 2.1 Modular Monolith — Justificativa

Sigo estritamente a recomendação de **Modular Monolith** como arquitetura primária.

**Por que NÃO Microservices para MVP:**

| Critério | Modular Monolith | Microservices |
|----------|-----------------|---------------|
| Complexidade operacional | Baixa (1 deploy) | Alta (N deploys, service mesh, etc.) |
| Latência entre serviços | In-process (μs) | Rede (ms a 100s de ms) |
| Transactional consistency | ACID nativo | Distributed transactions (Saga, eventual consistency) |
| Debugging/Traçamento | Straightforward | Complexo (distributed tracing obrigatório) |
| Custo de infra | 1 container / 1 app | Múltiplos containers + service discovery |
| Curva de aprendizado | Normal | Alta |
| MVP time-to-market | Semanas | Meses |
| Portfólio value | Mostra arquitetura limpa, DDD, boundaries bem definidos | Mostra DevOps avançado mas o código pode ser fraco |

**Quando migrar para Microservices (futuro):**
- Quando um módulo específico (ex: scraping) precisar escalar independentemente
- Quando equipes diferentes trabalharem em módulos distintos
- Quando houver justificativa de custo real (não hipotética)

### 2.2 Camada de Arquitetura

```
┌─────────────────────────────────────────────────┐
│                  Frontend (Next.js)              │
│    React + TypeScript + shadcn/ui + TanStack Query │
└──────────────────────┬──────────────────────────┘
                       │ REST API / SSE
┌──────────────────────▼──────────────────────────┐
│              FastAPI (Backend)                   │
│  ┌────────────────────────────────────────────┐  │
│  │           API Layer (Controllers)          │  │
│  ├────────────────────────────────────────────┤  │
│  │           Application Layer (Use Cases)    │  │
│  ├────────────────────────────────────────────┤  │
│  │        Domain Layer (Entities, AGGs)       │  │
│  ├────────────────────────────────────────────┤  │
│  │        Infrastructure Layer (Repos,       │  │
│  │        External Services, Adapters)        │  │
│  └────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────┤
│  PostgreSQL  │  Redis  │  Celery Workers        │
└──────────────────────────────────────────────────┘
```

**Princípios aplicados:**
- **Clean Architecture**: dependências apontam sempre para dentro (infra → domain)
- **Dependency Inversion**: interfaces no domínio, implementações na infra
- **Repository Pattern**: abstração de acesso a dados com SQLAlchemy
- **CQRS lite**: separação de leitura/escrita para queries complexas (analytics)
- **Event-Driven**: Celery tasks como event handlers pub/sub via Redis

### 2.3 Módulos do Monolito

```
backend/
├── modules/
│   ├── auth/           # Autenticação, autorização, sessões
│   ├── users/          # Gestão de perfil de usuário
│   ├── jobs/           # Vagas, buscadores, matching
│   ├── applications/   # Candidaturas, status tracking
│   ├── resume/         # Currículos, ATS scoring
│   ├── cover_letters/  # Geração de cartas
│   ├── ai/             # LLM abstraction, providers
│   ├── notifications/  # Email, Discord, Telegram, Push
│   ├── analytics/      # Dashboard, métricas
│   ├── calendar/       # Agenda, lembretes
│   └── config/         # Configurações da aplicação
```

Cada módulo tem sua própria pasta com `domain/`, `application/`, `infrastructure/`, `api/`.

---

## 3. Justificativa de Cada Tecnologia

### 3.1 Tecnologias Escolhidas

| Camada | Tecnologia | Justificativa | Alternativa Rejeitada | Motivo da Rejeição |
|--------|-----------|---------------|----------------------|-------------------|
| **Frontend Framework** | Next.js 14+ (App Router) | SSR/SSG nativo, SEO para landing page, API routes para webhooks | Nuxt.js, Astro | Next.js tem melhor ecossistema React + Vercel deploy patterns |
| **UI Components** | shadcn/ui | Headless, customizable, Tailwind-native, sem runtime extra | Radix, Chakra, MUI | shadcn/ui é mais leves e se integra perfeitamente com Tailwind |
| **Animations** | Framer Motion | Layout animations, gesturas, SSR-safe | React Spring | Mel DX, mais integrado com React idioms |
| **Data Fetching** | TanStack Query | Cache inteligente, stale-while-revalidate, mutations, pessimistic updates | SWR | TanStack Query é o successor espiritual do React Query com mais features |
| **Forms** | React Hook Form + Zod | Performance (sem re-renders desnecessários), validação tipo-safe | Formik | RHF é mais performático e tem melhor DX com Zod |
| **Backend** | FastAPI | Async-native, OpenAPI automático, Pydantic validation, tipagem forte | Django REST, Flask | FastAPI é o melhor para APIs modernas async + tipagem Python |
| **ORM** | SQLAlchemy 2.0 | Maduro, bem testado, suporta async, migration com Alembic | Tortoise, SQLModel | SQLModel limita flexibilidade; SQLAlchemy 2.0 é o padrão da indústria Python |
| **Task Queue** | Celery + Redis | Simples, bem documentado, bom ecossistema para FastAPI | Temporal | Temporal é poderoso mas adiciona complexidade desproporcional para MVP. Celery resolve 100% dos casos de uso atuais |
| **Cache** | Redis | Pub/sub para eventos, cache deLLM results, broker Celery | Memcached | Redis faz tudo (broker + cache + pub/sub) |
| **Database** | PostgreSQL | JSONB para dados flexíveis, full-text search, pgvector opcional futuro | MySQL | Postgres é mais robusto para analytics e tem melhores features |
| **Auth** | Better Auth | Open-source, autohospedável, suporta OAuth, magic links, session | Clerk | Clerk é SaaS gerenciado — dependência externa, menos controle, custo escala |
| **LLM Abstraction** | Strategy/Adapter Pattern | Interface comum com factory + strategy | LangChain abstrata | LangChain acopla demais; nossa abstração é mais enxuta e focada |
| **Infrastructure** | Docker + Docker Compose | Reprodutibilidade local, padrão da indústria | Podman, manual | Docker tem melhor ecossistema e CI/CD integrations |
| **Deployment** | Coolify (self-hosted) + Railway | Coolify = self-hosted PaaS; Railway = deploy rápido para staging | Vercel-only | Coolify permite self-hosting completo (importante para SaaS com dados de usuários) |

### 3.2 Abstração LLM — Design Detalhado

```python
# interface base (port/domain)
class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str: ...
    
    @abstractmethod
    async def summarize(self, text: str, **kwargs) -> str: ...
    
    @abstractmethod
    async def analyze_resume(self, resume: str, job_desc: str) -> dict: ...
    
    @abstractmethod
    async def compare_job(self, resume: str, job: dict) -> dict: ...
    
    @abstractmethod
    async def generate_cover_letter(self, resume: str, job: dict) -> str: ...
```

Cada provider implementa essa interface. O `LLMService` usa **Strategy Pattern** com factory baseado na configuração do usuário:

```python
class LLMService:
    def __init__(self, provider: LLMProvider):
        self._provider = provider
    
    async def generate(self, prompt, **kwargs):
        return await self._provider.generate(prompt, **kwargs)
```

**Decisão importante**: não usar LangChain como abstração principal. LangChain é um framework enorme que atrapalha a clareza da arquitetura Clean Architecture. Usamos LangChain/SDKs das APIs apenas dentro de cada provider (adapter), nunca atravessando a boundary do domínio.

**Modelo de custo**: cada usuário configura sua própria API key. O service de LLM adiciona caching de resultados (Redis TTL) para evitar chamadas duplicadas — isso reduz custos para o usuário e melhora performance.

### 3.3 Melhoria na Stack: Adições que Proponho

**Ponto de discussão:**

| Alteração | Proposta | Justificativa |
|-----------|---------|---------------|
| **Message Broker** | Adicionar Apache Kafka (ou Redis Streams) | Event-driven entre módulos (ex: vaga encontrada → matching → notificação). Redis Streams já vem com Redis, sem dependência extra |
| **Vector DB** | Adicionar pgvector (extensão PostgreSQL) | Para matching semântico de vagas e currículos. Não é urgente para MVP mas é o caminho para v2 |
| **Observabilidade** | Sentry + Prometheus + Grafana (ou Better Stack) | Logs estruturados + alerting + métricas. Essencial para SaaS em produção |
| **Testes** | pytest + httpx + Playwright | Backend: pytest. Frontend: Vitest + Testing Library. E2E: Playwright |
| **CI/CD** | GitHub Actions | Build, test, lint, security scan, deploy |
| **API Documentation** | OpenAPI (nativo FastAPI) + Swagger UI | Já incluso no stack |

---

## 4. Estrutura de Pastas

```
jobpilot-ai/
├── apps/
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── app/                    # Next.js App Router pages
│   │   │   ├── components/
│   │   │   │   ├── ui/                 # shadcn/ui components
│   │   │   │   ├── dashboard/
│   │   │   │   ├── jobs/
│   │   │   │   ├── resume/
│   │   │   │   ├── ai-chat/
│   │   │   │   └── layout/
│   │   │   ├── hooks/                # TanStack Query hooks
│   │   │   ├── lib/                  # Utilities, API clients
│   │   │   ├── schemas/              # Zod schemas
│   │   │   ├── stores/               # Zustand (if needed beyond TanStack)
│   │   │   └── types/                # TypeScript types
│   │   ├── public/
│   │   ├── .env.local
│   │   ├── next.config.js
│   │   ├── tailwind.config.ts
│   │   └── tsconfig.json
│   │
│   └── backend/
│       ├── src/
│       │   ├── api/                  # FastAPI routes (thin controllers)
│       │   │   ├── v1/
│       │   │   │   ├── auth.py
│       │   │   │   ├── users.py
│       │   │   │   ├── jobs.py
│       │   │   │   ├── applications.py
│       │   │   │   ├── resume.py
│       │   │   │   ├── ai.py
│       │   │   │   └── ...
│       │   │
│       │   ├── modules/              # Clean Architecture modules
│       │   │   ├── auth/
│       │   │   │   ├── domain/
│       │   │   │   │   ├── entities.py
│       │   │   │   │   └── repositories.py    # interfaces (Abstract base)
│       │   │   │   ├── application/
│       │   │   │   │   ├── use_cases.py
│       │   │   │   │   └── dto.py
│       │   │   │   ├── infrastructure/
│       │   │   │   │   ├── repositories.py    # SQLAlchemy impl
│       │   │   │   │   └── providers.py       # Better Auth impl
│       │   │   │   └── api/
│       │   │   │       └── routes.py
│       │   │   │
│       │   │   ├── users/
│       │   │   ├── jobs/
│       │   │   ├── applications/
│       │   │   ├── resume/
│       │   │   ├── cover_letters/
│       │   │   ├── ai/
│       │   │   │   ├── domain/
│       │   │   │   │   ├── entities.py
│       │   │   │   │   └── repositories.py
│       │   │   │   ├── application/
│       │   │   │   │   ├── use_cases.py
│       │   │   │   │   ├── services.py        # LLMService, ScoringService
│       │   │   │   │   └── dto.py
│       │   │   │   ├── infrastructure/
│       │   │   │   │   ├── providers/
│       │   │   │   │   │   ├── base.py         # ABC for LLMProvider
│       │   │   │   │   │   ├── openai_provider.py
│       │   │   │   │   │   ├── anthropic_provider.py
│       │   │   │   │   │   ├── gemini_provider.py
│       │   │   │   │   │   ├── ollama_provider.py
│       │   │   │   │   │   ├── nvidi_nim_provider.py
│       │   │   │   │   │   └── openrouter_provider.py
│       │   │   │   │   └── repositories.py
│       │   │   │   └── api/
│       │   │   │       └── routes.py
│       │   │   ├── notifications/
│       │   │   ├── analytics/
│       │   │   ├── calendar/
│       │   │   └── config/
│       │   │
│       │   ├── core/                   # Shared cross-cutting concerns
│       │   │   ├── database.py          # SQLAlchemy engine, session, base
│       │   │   ├── redis_client.py      # Redis connection pool
│       │   │   ├── logger.py            # Structured logging (structlog)
│       │   │   ├── security.py          # Encryption, hashing
│       │   │   ├── exceptions.py        # Custom exceptions
│       │   │   ├── middleware.py        # Auth middleware, rate limiting
│       │   │   └── config.py            # Settings (pydantic-settings)
│       │   │
│       │   ├── workers/                # Celery tasks
│       │   │   ├── scraping.py
│       │   │   ├── matching.py
│       │   │   ├── ats_scoring.py
│       │   │   ├── email_notifications.py
│       │   │   └── ...
│       │   │
│       │   ├── main.py                # FastAPI app factory
│       │   └── dependency_injection.py # WireUp (DI container)
│       │
│       ├── alembic/                   # DB migrations
│       ├── tests/
│       │   ├── unit/
│       │   ├── integration/
│       │   └── conftest.py
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── requirements-dev.txt
│       ├── celeryworker.Dockerfile
│       └── pyproject.toml             # Poetry or uv
│
├── infra/
│   ├── docker/
│   │   ├── nginx/                     # Reverse proxy config
│   │   ├── postgres/
│   │   ├── redis/
│   │   └── vector/                    # Optional: pgvector config
│   ├── docker-compose.yml              # Local development
│   ├── docker-compose.prod.yml         # Production overrides
│   ├── coolify/                        # Coolify deployment manifests
│   └── railway.json                    # Railway deployment config
│
├── docs/
│   ├── architecture.md
│   ├── api.md                         # OpenAPI spec generated
│   └── database.md                    # ER diagram
│
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── cd.yml
│
├── .env.example
├── .gitignore
├── README.md
├── CLAUDE.md                          # Project memory for future sessions
├── PLAN.md                            # This file
└── AGENTS.md                          # Agent guidelines
```

---

## 5. Modelagem do Banco de Dados

### 5.1 Diagrama ER (Entidades Principais)

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────┐
│    users      │─────│  user_settings   │─────│  llm_providers│
│─────────────│     │─────────────────│     │──────────────│
│ id (PK)      │     │ user_id (FK)    │     │ id (PK)       │
│ email        │     │ theme            │     │ provider_name │
│ password_hash│     │ language         │     │ api_key_enc   │
│ full_name    │     │ notifications   │     │ model         │
│ created_at   │     │ provider        │     │ base_url      │
│ updated_at   │     └─────────────────┘     │ is_active     │
└─────────────┘                              │ user_id (FK)  │
                                             └──────────────┘
                                                   │
┌─────────────┐     ┌─────────────────┐    ┌────▼──────────────┐
│  companies   │     │    resumes       │◄───│  user_providers   │
│─────────────│     │─────────────────│    │───────────────────│
│ id (PK)      │     │ id (PK)         │    │ id (PK)           │
│ name         │     │ user_id (FK)    │    │ llm_provider_id   │
│ website      │     │ title           │    │ (alias de uso)    │
│ industry     │     │ file_url        │    └───────────────────┘
│ location     │     │ content_text    │
└─────────────┘     │ ats_score        │
                     │ ats_breakdown    │
┌─────────────────┐  │ jsonb            │
│  experiences    │  └─────────────────┘
│─────────────────│
│ id (PK)         │  ┌─────────────────┐     ┌────────────────┐
│ resume_id (FK)  │  │  skills          │─────│  job_sources   │
│ company         │  │─────────────────│     │────────────────│
│ role            │  │ id (PK)          │     │ id (PK)        │
│ start_date      │  │ name             │     │ name           │
│ end_date        │  │ category        │     │ type (api/scrape│
│ is_current      │  │ level           │     │ source_url     │
│ created_at      │  │ user_id (FK)    │     │ is_active      │
└─────────────────┘  └─────────────────┘     └────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌────────────────┐
│    jobs         │─────│  job_requirements│     │ job_matches    │
│─────────────────│     │─────────────────│     │────────────────│
│ id (PK)         │     │ job_id (FK)     │     │ id (PK)        │
│ source          │     │ requirement     │     │ job_id (FK)    │
│ title           │     │ is_must_have    │     │ resume_id (FK) │
│ company_id (FK) │     │ category       │     │ score          │
│ description     │     │ raw_text        │     │ match_reasons  │  ← JSONB
│ responsibilities│     └─────────────────┘     │ suggestions    │  ← JSONB
│ seniority       │                             │ matched_skills │  ← JSONB
│ location_type   │                             │ missing_skills │  ← JSONB
│ salary_min      │                             │ score_details  │  ← JSONB
│ salary_max      │                             │ created_at     │
│ currency        │                             └────────────────┘
│ apply_url       │
│ source_url      │─────► job_applications ◄─────┐
│ posted_at       │     ┌─────────────────┐       │
│ is_remote       │     │ applications     │       │
│ metadata_jsonb  │     │─────────────────│       │
└─────────────────┘     │ id (PK)         │       └────────────────┘
                        │ job_id (FK)     │             │
┌─────────────────┐     │ resume_id (FK)  │             │
│  applications   │─────│ status           │             │
│─────────────────│     │ (enum)          │             │
│ id (PK)         │     │ cover_letter    │             │
│ job_id (FK)     │     │ custom_message  │             │
│ resume_id (FK)  │     │ applied_at      │             │
│ cover_letter_id │     │ responded_at    │             │
│ status          │     │ source_platform │             │
│ source_platform │     │ track_data      │  ┌────────────────┐
│ applied_at      │     │ jsonb            │  │  interviews     │
│ responded_at    │     └─────────────────┘  │────────────────│
│ tracking_data   │                          │ id (PK)        │
└─────────────────┘                          │ application_id FK│
                                             │ type            │
┌─────────────────┐                          │ date            │
│  ai_analyses     │                          │ company         │
│─────────────────│                          │ stage           │
│ id (PK)         │                          │ notes           │
│ user_id (FK)    │                          │ created_at      │
│ analyzable_id   │                          └────────────────┘
│ analyzable_type │
│ analysis_type   │  ┌─────────────────┐     ┌────────────────┐
│ result (jsonb)  │  │  notifications   │     │  events        │
│ score           │  │─────────────────│     │────────────────│
│ tokens_used     │  │ id (PK)         │     │ id (PK)        │
│ model_used      │  │ user_id (FK)    │     │ event_type     │
│ created_at      │  │ type            │     │ entity_type    │
└─────────────────┘  │ title           │     │ entity_id      │
                     │ message         │     │ metadata       │
                     │ channel         │     │ created_at     │
                     │ status          │     └────────────────┘
                     │ read_at         │
                     └─────────────────┘

┌─────────────────┐     ┌─────────────────┐
│  calendar_events│     │  search_preferences│
│─────────────────│     │─────────────────│
│ id (PK)         │     │ user_id (FK)    │
│ user_id (FK)    │     │ filters (jsonb) │
│ title           │     │ saved_searches  │  ← JSONB array
│ event_type      │     │ alerts_enabled  │
│ date            │     │ notify_via      │  ← JSONB array of channels
│ notes           │     │ frequency       │
│ location        │     └─────────────────┘
│ status          │
│ reminders       │
└─────────────────┘
```

### 5.2 Decisions de Banco

- **JSONB** para dados flexíveis (match_reasons, suggestions, tracking_data) — permite queries e indexing posterior
- **Enum** para status de aplicação e notificação — força consistência no DB
- **pgvector** (extensão) está preparado para a próxima versão, quando implementar matching semântico
- **Indexes** em: `jobs(source, posted_at)`, `applications(user_id, status)`, `resume(user_id)`
- **Soft deletes** via coluna `deleted_at` (não apagar dados, marcar como deletado)

---

## 6. Roadmap Completo

### Fase 0 — Fundação (Semanas 1-3)

| Semana | Entrega |
|--------|---------|
| 1 | Setup do monorepo, Docker Compose local, esqueleto do backend FastAPI com estrutura de módulos, configurador de ambiente |
| 2 | Auth module (Better Auth + migration), primeira rota de saúde, middleware de auth, testes básicos |
| 3 | Database models (SQLAlchemy), Alembic migrations setup, seed scripts, CI pipeline básico |

### Fase 1 — Core MVP (Semanas 4-8)

| Semana | Entrega |
|--------|---------|
| 4 | Users module (CRUD completo), profile endpoints, Zod schemas frontend |
| 5 | Resume module (upload PDF, armazenamento, parsing básico com IA) |
| 6 | AI provider abstraction (3 providers: OpenAI, Ollama, NVIDIA NIM), LLMService com cache Redis |
| 7 | Jobs module — integration com 2 sources (Gupy API + Indeed API), busca com filtros |
| 8 | Matching engine básico (keyword matching + AI scoring), ATS Score básico |

### Fase 2 — Candidaturas e Matching (Semanas 9-13)

| Semana | Entrega |
|--------|---------|
| 9 | Applications module (status tracking, CRUD), Rastreamento de status completo |
| 10 | Cover letter generator (AI), Currículo inteligente personalizado por vaga |
| 11 | Matching inteligente com motivos e sugestões detalhadas |
| 12 | Dashboard MVP (métricas essenciais: vagas, candidaturas, scores) |
| 13 | Notificações básicas (email via Resend/SendGrid, Discord webhook) |

### Fase 3 — Analytics & Assistente (Semanas 14-18)

| Semana | Entrega |
|--------|---------|
| 14 | Chat assistente IA (SSE streaming) com contexto do perfil do usuário |
| 15 | Analytics avançados (taxa de entrevistas, empresas com maior retorno, tecnologias mais exigidas) |
| 16 | Calendar/Schedule module (integração com Google Calendar + notificações) |
| 17 | Importação inteligente (LinkedIn public profile scraping — respeitando ToS, GitHub API) |
| 18 | Polish geral, testes de integração, performance, staging deploy |

### Fase 4 — Hardening e Produção (Semanas 19-22)

| Semana | Entrega |
|--------|---------|
| 19 | Automação de candidaturas (preencher formulários quando permitido) |
| 20 | Background workers (Celery) para todas as tarefas pesadas (scraping, matching, AI) |
| 21 | Observabilidade (Sentry, logging estruturado, métricas), alerting |
| 22 | Production deploy (Coolify/Railway), stress testing, security audit, documentation final |

### Fase 5 — Evolução (Pós-MVP — Trimestre 4+)

| Entrega | Descrição |
|---------|-----------|
| JobPilot Agent | Agente autônomo que monitora vagas e candidata automaticamente |
| Vector Search | pgvector para matching semântico avançado |
| Multi-tenancy | Suporte a múltiplos usuários com isolamento de dados |
| Payment/Subscription | Monetização tiered |
| Email Campaigns | Envio em massa de candidaturas (com respeito aos limites) |
| Chrome Extension | Extensão para ver matching score enquanto navega em job boards |
| Mobile App | React Native ou Expo |

---

## 7. MVP Definido

### MVP = Fase 0 + Fase 1 (Semanas 1-8)

**O que está no MVP:**
- ✅ Auth completo (registro, login, session)
- ✅ CRUD de perfil de usuário
- ✅ Upload e parsing de currículo PDF
- ✅ 3 provedores LLM configuráveis por usuário
- ✅ Buscador de vagas (2 fontes: Gupy + Indeed via API)
- ✅ Matching básico com score percentual
- ✅ ATS Score básico
- ✅ Geração de cover letter com IA
- ✅ Rastreamento manual de candidaturas

**O que NÃO está no MVP:**
- ❌ Scraping de LinkedIn (risco legal/técnico)
- ❌ Automação de candidaturas (complexidade alta + risco)
- ❌ Chat assistente IA (depende do matching estar robusto)
- ❌ Analytics avançados
- ❌ Notificações Discord/Telegram/Push
- ❌ Agenda com integração de calendário
- ❌ Abordagem multi-plataforma completa

**Critério de sucesso do MVP:** Um usuário cadastra-se, faz upload do currículo, configura seu provedor LLM, busca vagas no Gupy/Indeed, recebe matching scores, e submete candidaturas manualmente com cover letters geradas.

---

## 8. Riscos Identificados

### 8.1 Riscos Técnicos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| APIs de job boards mudam/limitam accesso | Alta | Alto | Adapter pattern para cada source; fallback entre APIs; caching agressivo |
| Custos de LLM escalarem | Média | Alto | Redis caching de resultados de IA; budget tracking por usuário; Ollama como opção free |
| PDF parsing impreciso | Média | Médio | Usar Azure Document Intelligence ou AWS Textract como fallback; validação humana |
| Scraping de sites sem API quebra facilmente | Alta | Médio | Não depender de scraping para fontes primárias; usar APIs oficiais quando possível |
| PostgreSQL performance em queries de matching | Baixa | Médio | Indexação adequada; query optimization; considerar desacoplar matching para read-replica no futuro |
| Celery worker falha silentemente | Baixa | Alto | Health checks; monitoring de fila; dead letter queue |

### 8.2 Riscos Legais

| Risco | Mitigação |
|-------|----------|
| Violação de ToS ao scrapear job boards | Documentação explícita; priorizar APIs oficiais; disclaimer nos termos de serviço |
| Dados pessoais de usuários (GDPR/CCPA) | Privacy-first design; criptografia de API keys; possibilidade de apagar todos os dados do usuário; política de retenção |
| IA gerar informações falsas no currículo | Guardrails: nunca inventar experiências; apenas reorganizar dados existentes; disclaimer ao usuário |
| Automação de candidaturas violar ToS | Apenas automatizar quando a plataforma permite explicitamente; never bypass CAPTCHAs ou auth |

### 8.3 Riscos de Manutenção

| Risco | Mitigação |
|-------|----------|
| Dependência de APIs de terceiros que mudam | Interface adapter isolada por provider; testes de integração; monitoring de health check por fonte |
| Debt técnico acumular | Code review obrigatório; tests obrigatórios antes de merge; tech debt tracking no backlog |
| Documentação cair atrás do código | Docs como código (OpenAPI specs geradas, DB schema diagrams versionados) |

### 8.4 Riscos de Escalabilidade (futuro)

| Risco | Quando se manifesta | Mitigação |
|-------|---------------------|-----------|
| Celery workers não escalam bem | > 1000 usuários | Migrar para Kubernetes ou serverless (AWS Lambda para workers) |
| LLM costs explode com muitos usuários | > 500 usuarios ativos | Implementar rate limiting por usuário; pooling de requests para mesmo prompt; caching agressivo |
| Banco de dados se torna gargalo | > 5000 usuarios | Read replicas; connection pooling (PgBouncer); caching Redis para queries frequentes |

---

## 9. Pontos de Decisão para Discussão

Antes de aprovar, apresento 5 decisões que quero discutir com você:

### P1: Better Auth vs Clerk
- **Melhor Auth**: open-source, self-hostable, controle total, sem vendor lock-in. Mas requer mais setup e manutenção de email sending.
- **Clerk**: DX superior, managed, email/SSO já inclusos. Mas dependente de serviço externo e custo pode escalar.
- **Minha recomendação**: Better Auth — alinha com o self-hosted philosophy do projeto.
- **Concorda?**

### P2: Celery vs Temporal
- **Celery**: simples, maduro, suficiente para 100% dos casos de uso atuais. Redis como broker está incluído no stack.
- **Temporal**: workflow orchestration complexa para workflows com compensação, retry stateful. Overkill para MVP.
- **Minha recomendação**: Celery para MVP, avaliar Temporal se migrarmos para microservices.
- **Concorda?**

### P3: Auth: PostgreSQL-only vs Separate Auth Service
- Para MVP, auth dentro do mesmo banco simplifica tudo. No futuro, podemos extrair para um auth service separado se necessário.
- **Minha recomendação**: Auth no banco atual (modularmente isolado no módulo `auth/`).
- **Concorda?**

### P4: Frontend: single Next.js app vs separate frontend/backend repos
- Mono-repo do Next.js + FastAPI é mais simples para começar e permite compartilhar tipos Zod ↔ Pydantic.
- **Minha recomendação**: Monorepo com frontend e backend no mesmo repo.
- **Concorda?**

### P5: Deploy Target Principal
- **Coolify**: self-hosted PaaS, controle total, custo previsível ideal para long-term SaaS. Mas requer que você tenha um VPS.
- **Railway**: mais fácil para deploy rápido, bom para staging. Mas custo por uso pode ficar caro e menos controle.
- **Minha recomendação**: Coolify como produção + Railway para staging temporário durante desenvolvimento.
- **Concorda?**

---

## Próximos Passos

1. **Apresentar este plano para revisão**
2. **Discutir os 5 pontos de decisão acima**
3. **Após aprovação, iniciar Fase 0 (Fundação)**
4. **Primeiro commit será o scaffolding do monorepo com Docker Compose**

---

*Documento gerado por: Tech Lead — JobPilot AI Architecture Review*
*Próximo checkpoint: Aprovação do plano antes de implementação*
