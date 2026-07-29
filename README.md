# JobPilot AI 🚀

**Copiloto de carreira inteligente** que automatiza e otimiza a busca por emprego.
JobPilot AI usa inteligência artificial multi-provedor para ajudar candidatos a encontrar vagas compatíveis, analisar currículos, gerar cartas de apresentação personalizadas e acompanhar candidaturas — tudo em um só lugar.

---

## ✨ Funcionalidades

| Funcionalidade | Status |
|---------------|--------|
| 🔐 Autenticação (register/login/logout com sessions) | ✅ Pronto |
| 👤 Perfil de usuário | ✅ Pronto |
| 📄 Upload e parsing de currículo PDF | ✅ Pronto |
| 🤖 Abstração multi-provedor LLM (OpenAI, Anthropic, Gemini, Ollama, NVIDIA NIM, OpenRouter) | ✅ Pronto |
| 💼 Busca de vagas (Gupy API + banco local) | ✅ Pronto |
| 📊 Análise de currículo vs vaga com IA (matching + ATS Score) | ✅ Pronto |
| ✉️ Geração de cartas de apresentação com IA | ✅ Pronto |
| 📋 Rastreamento de candidaturas (pipeline completo) | ✅ Pronto |
| 🔔 Notificações multi-canal (Email, Discord, Telegram) | ✅ Pronto |
| ⚡ Tarefas assíncronas com Celery | ✅ Pronto |
| 📈 Analytics de carreira | 📅 Planejado |
| 🗓️ Agenda de entrevistas | 📅 Planejado |
| 🤖 Chat assistente IA | 📅 Planejado |

---

## 🛠️ Stack

| Camada | Tecnologia |
|--------|-----------|
| **Frontend** | Next.js 14 + React + TypeScript + TailwindCSS + shadcn/ui |
| **Backend** | FastAPI (Python 3.12+) |
| **Database** | PostgreSQL 16 |
| **Cache / Broker** | Redis 7 |
| **Task Queue** | Celery + Redis |
| **Auth** | Session-based com tokens |
| **LLM** | Multi-provedor (Strategy Pattern) |
| **Container** | Docker + Docker Compose |
| **CI/CD** | GitHub Actions |

---

## 📁 Estrutura do Projeto

```
jobpilot-ai/
├── apps/
│   ├── frontend/                    # Next.js application
│   │   ├── src/
│   │   │   ├── app/                 # App Router pages
│   │   │   ├── components/          # UI components
│   │   │   │   ├── ui/              # shadcn/ui
│   │   │   │   ├── dashboard/
│   │   │   │   ├── jobs/
│   │   │   │   └── resume/
│   │   │   ├── hooks/               # TanStack Query hooks
│   │   │   ├── lib/                 # Utilities
│   │   │   └── types/               # TypeScript types
│   │   ├── package.json
│   │   └── next.config.js
│   │
│   └── backend/                     # FastAPI application
│       ├── src/
│       │   ├── main.py              # App factory + router wiring
│       │   ├── core/                # Cross-cutting concerns
│       │   │   ├── config.py        # Pydantic settings
│       │   │   ├── database.py      # Async SQLAlchemy engine
│       │   │   ├── models.py        # 18 ORM models
│       │   │   ├── redis_client.py  # Redis connection
│       │   │   ├── security.py      # Fernet encryption
│       │   │   ├── logger.py        # structlog config
│       │   │   ├── middleware.py    # Request logging + auth
│       │   │   ├── exceptions.py    # Domain exceptions
│       │   │   └── dependency_injection.py
│       │   ├── modules/             # Clean Architecture modules
│       │   │   ├── auth/            # Autenticação
│       │   │   ├── users/           # Perfil de usuário
│       │   │   ├── jobs/            # Vagas + buscadores
│       │   │   ├── resume/          # Currículos + PDF parsing
│       │   │   ├── cover_letters/   # Geração de cartas
│       │   │   ├── applications/    # Candidaturas + tracking
│       │   │   ├── notifications/   # Email/Discord/Telegram
│       │   │   ├── ai/              # LLM abstraction + providers
│       │   │   ├── analytics/       # Métricas (planejado)
│       │   │   └── calendar/        # Agenda (planejado)
│       │   └── workers/             # Celery tasks
│       ├── alembic/                 # Database migrations
│       ├── tests/                   # Testes
│       ├── Dockerfile
│       ├── requirements.txt
│       └── pyproject.toml
│
├── infra/
│   ├── docker/
│   │   ├── nginx/                   # Reverse proxy config
│   │   └── postgres/                # Init scripts
│   ├── coolify/                     # Coolify manifests
│   └── railway.json                 # Railway config
│
├── .github/workflows/               # CI/CD pipelines
├── docker-compose.yml               # Local dev stack
├── .env.example                     # Environment template
├── PLAN.md                          # Roadmap detalhado
└── README.md                        # Este arquivo
```

---

## 🚀 Execução Rápida

### Pré-requisitos
- Docker e Docker Compose v2
- Python 3.12+ (desenvolvimento local)
- Node.js 20+ (desenvolvimento frontend)

### Com Docker (recomendado)

```bash
# Clone e entre no diretório
git clone https://github.com/blackxzin/JOBPILOT_AI.git
cd JOBPILOT_AI

# Configure o ambiente
cp .env.example .env

# Suba todos os serviços
docker compose up -d

# Pronto! Acesse:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - Swagger Docs: http://localhost:8000/docs
# - Redoc: http://localhost:8000/redoc
```

### Desenvolvimento Local (Backend)

```bash
cd apps/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

### Desenvolvimento Local (Frontend)

```bash
cd apps/frontend
npm install
npm run dev
```

---

## 📡 API Endpoints

Todas as rotas usam prefixo `/api/v1`.

### Autenticação
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/auth/register` | Registrar novo usuário |
| POST | `/auth/login` | Login (retorna token) |
| POST | `/auth/logout` | Invalidar sessão |
| GET | `/auth/me` | Dados do usuário logado |

### Perfil
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/users/me/profile` | Perfil do usuário logado |

### Vagas
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/jobs` | Buscar vagas locais |
| GET | `/jobs/gupy` | Buscar vagas na Gupy |
| GET | `/jobs/{id}` | Detalhes de uma vaga |

### Currículos
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/resumes/upload` | Upload de PDF (extrai texto automaticamente) |
| GET | `/resumes/list` | Listar currículos do usuário |
| GET | `/resumes/{id}` | Detalhes de um currículo |

### Cartas de Apresentação
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/cover-letters/generate` | Gerar carta com IA para uma vaga |

### Candidaturas
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/applications` | Registrar candidatura |
| GET | `/applications/list` | Listar candidaturas (com filtros) |
| GET | `/applications/stats` | Estatísticas agregadas |
| PATCH | `/applications/{id}/status` | Atualizar status |

### Notificações
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/notifications` | Listar notificações |
| GET | `/notifications/unread-count` | Contagem de não lidas |
| PATCH | `/notifications/{id}/read` | Marcar como lida |

### Saúde
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/health` | Health check do serviço |

---

## 🧠 Arquitetura de IA

JobPilot usa **Strategy Pattern** para abstrair múltiplos provedores LLM:

```
┌────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│   LLMService   │────▶│  LLMProvider     │◀────│  OpenAIProvider   │
│  (Application) │     │   (Domain)       │     ├───────────────────┤
│                │     │                  │────▶│ AnthropicProvider │
│ - generate     │     │ - analyze_resume │     ├───────────────────┤
│ - summarize    │     │ - compare_job    │────▶│  GeminiProvider   │
│ - analyze      │     │ - cover_letter   │     ├───────────────────┤
│ - compare      │     │ - health_check   │────▶│  OllamaProvider   │
│ - cover_letter │     └──────────────────┘     ├───────────────────┤
└────────────────┘                              │ NVIDIA NIM        │
                                                ├───────────────────┤
        ┌──────────────┐                        │ OpenRouter        │
        │   Factory    │                        └───────────────────┘
        │ (Cria provider│
        │  baseado na   │
        │ configuração  │
        │  do usuário)  │
        └──────────────┘
```

Cada usuário configura sua própria API key no banco (criptografada com Fernet).
Resultados de IA são cacheados no Redis para reduzir custos.

---

## 📊 Banco de Dados

18 tabelas principais:
- **users**, **sessions**, **user_settings**
- **resumes**, **experiences**, **skills**
- **companies**, **jobs**, **job_requirements**, **job_matches**
- **applications**, **interviews**
- **cover_letters**
- **ai_analyses**
- **llm_provider_configs**
- **notifications**
- **calendar_events**, **search_preferences**
- **events** (audit log)

Para migrações: `cd apps/backend && alembic upgrade head`

---

## 🐳 Serviços Docker

| Serviço | Porta | Descrição |
|---------|-------|-----------|
| `postgres` | 5432 | Banco de dados |
| `redis` | 6379 | Cache + Celery broker |
| `backend` | 8000 | API FastAPI |
| `celery-worker` | — | Workers assíncronos |
| `celery-beat` | — | Tarefas agendadas |
| `frontend` | 3000 | Next.js |
| `nginx` | 80/443 | Reverse proxy |

---

## 🧪 Testes

```bash
cd apps/backend
pip install -r requirements.txt pytest pytest-asyncio httpx aiosqlite
pytest tests/ -v --asyncio-mode=auto
```

---

## 🚢 Deploy

Opções suportadas:
- **Coolify** (self-hosted) — produção
- **Railway** — staging rápido
- **Docker Compose** — deploy single-server

---

## 📄 Licença

MIT

---

**Feito com dedicação por [Lucas Oliver](https://github.com/lucasoliver43322)**
