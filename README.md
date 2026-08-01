# JobPilot AI 🚀

**Copiloto de carreira inteligente** que automatiza e otimiza a busca por emprego.
Usa IA multi-provedor pra encontrar vagas compatíveis, analisar currículos, gerar cartas personalizadas, currículo inteligente, e acompanhar candidaturas — tudo num só lugar.

---

## ✨ Funcionalidades

### Backend (FastAPI + Python)

| Módulo | Status | O que faz |
|--------|--------|-----------|
| 🔐 **Auth** | ✅ | Register, login, logout, sessão com tokens, LinkedIn OAuth |
| 👤 **Users** | ✅ | Perfil de usuário, proteção por token |
| 💼 **Jobs** | ✅ | Busca local + 6 fontes externas (RemoteOK, Indeed, LinkedIn Jobs, Programathor, GeekHunter, Gupy) + busca semântica pgvector |
| 🤖 **AI / LLM** | ✅ | 6 provedores (OpenAI, Anthropic, Gemini, NVIDIA NIM, Ollama, OpenRouter) — matching, ATS, cover letter, currículo inteligente, auto apply |
| 📄 **Resume** | ✅ | Upload PDF, extração de texto com pypdf, currículo personalizado por vaga |
| 📋 **Applications** | ✅ | Pipeline completo com status, CRUD, auto apply |
| ✉️ **Cover Letters** | ✅ | Geração automática com IA |
| 📅 **Calendar** | ✅ | Agenda de entrevistas, CRUD com status |
| 💬 **Chat** | ✅ | Assistente de carreira com IA |
| 🐙 **GitHub Import** | ✅ | Importa perfil, repositórios e skills via API |
| 🔗 **LinkedIn Analysis** | ✅ | Análise de perfil via IA |
| 📊 **Matching + ATS** | ✅ | Score de compatibilidade e análise de currículo vs vaga |
| 📊 **Analytics** | ✅ | KPIs (taxa entrevista/oferta/rejeição), top empresas, top skills, timeline |
| 🔔 **Notifications** | ✅ | Email (Resend), Discord webhook, Telegram bot |
| ⚡ **Celery Workers** | ✅ | Tasks assíncronas: scraping, matching, ATS, email, auto apply |
| 🧠 **Vector Search** | ✅ | Busca semântica com embeddings (pgvector) |

### Frontend (Next.js + React + Tailwind)

| Tela | Funcionalidades |
|------|----------------|
| **Login** | Email/senha, entrada rápida, login com LinkedIn OAuth, modo claro/escuro |
| **Dashboard** | KPIs, GitHub Import, LinkedIn Analysis, gráfico status, top empresas, top skills, timeline |
| **Jobs** | Busca em 6 fontes + busca semântica, filtros rápidos |
| **Calendar** | Criar/editar/deletar eventos de entrevista |
| **Applications** | Pipeline de status + Matching, ATS Score, Carta, Currículo Inteligente, Auto Apply |
| **Notifications** | 🔔 dropdown na navbar com contador, marca como lida |
| **Resumes** | Upload PDF, listagem |
| **Chat** | Assistente de carreira IA |
| **IA Settings** | Configurar chave dos 6 provedores |

---

## 🛠️ Stack

| Camada | Tecnologia |
|--------|-----------|
| **Frontend** | Next.js 14 + React 18 + TypeScript + TailwindCSS |
| **Backend** | FastAPI (Python 3.12+) |
| **Database** | PostgreSQL 16 + pgvector |
| **Cache / Broker** | Redis 7 |
| **Task Queue** | Celery + Redis |
| **Auth** | Session-based com tokens + LinkedIn OAuth |
| **LLM** | Multi-provedor (Strategy Pattern — 6 providers) |
| **Container** | Docker + Docker Compose (6 serviços) |
| **CI/CD** | GitHub Actions |
| **Testes** | pytest + pytest-asyncio (47 testes) |

---

## 📁 Estrutura do Projeto

```
JOBPILOT_AI/
├── apps/
│   ├── backend/                        # FastAPI
│   │   ├── src/
│   │   │   ├── main.py                 # App factory + routers
│   │   │   ├── core/                   # Config, DB, models, security, exceptions
│   │   │   ├── modules/                # Clean Architecture modules
│   │   │   │   ├── auth/               # Autenticação + LinkedIn OAuth
│   │   │   │   ├── users/              # Perfil + clients externos (Gupy, GitHub, etc.)
│   │   │   │   ├── jobs/               # Vagas + buscadores externos
│   │   │   │   ├── resume/             # Upload + parsing PDF
│   │   │   │   ├── cover_letters/      # Geração de cartas
│   │   │   │   ├── applications/       # Candidaturas + pipeline
│   │   │   │   ├── notifications/      # Email/Discord/Telegram
│   │   │   │   ├── ai/                 # LLM abstraction (6 providers)
│   │   │   │   ├── analytics/          # Métricas e KPIs
│   │   │   │   ├── calendar/           # Agenda
│   │   │   │   ├── config/             # Config de IA do usuário
│   │   │   │   └── search/             # Busca semântica pgvector
│   │   │   └── workers/                # Celery tasks
│   │   ├── tests/                       # 47 testes
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── frontend/                        # Next.js 14
│   │   ├── src/app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx                # SPA completa
│   │   │   └── globals.css             # Tema claro/escuro via CSS variables
│   │   ├── Dockerfile
│   │   └── package.json
│   │
│   └── docs/, infra/                   # Futuro
│
├── infra/
│   ├── docker/                         # nginx.conf + init.sql
│   └── coolify/, railway/              # Deploy guides
│
├── docker-compose.yml                   # 6 serviços (dev, sem nginx)
├── PLAN.md                              # Status detalhado
└── README.md                            # Este arquivo
```

---

## 🚀 Execução Rápida

### Com Docker (recomendado)

```bash
git clone https://github.com/blackxzin/JOBPILOT_AI.git
cd JOBPILOT_AI

cp .env.example .env
# Edite .env com suas chaves

# 💡 IA em dev usa NVIDIA NIM (grátis no build.nvidia.com):
# gere uma chave em https://build.nvidia.com (modelo meta/llama-3.2-3b-instruct)
# e coloque em OPENAI_API_KEY — é uma chave OpenAI-compatible da NVIDIA.

docker compose up -d

# Acesse:
# - Frontend: http://localhost:3000
# - API: http://localhost:8000
# - Docs: http://localhost:8000/docs
```

### Desenvolvimento Local

**Backend:**
```bash
cd apps/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

**Frontend:**
```bash
cd apps/frontend
npm install
npm run dev
```

**Testes:**
```bash
cd apps/backend
pip install -r requirements.txt pytest pytest-asyncio httpx aiosqlite numpy
PYTHONPATH=src pytest tests/ -v
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
| GET | `/auth/linkedin/login` | URL de login LinkedIn OAuth |
| GET | `/auth/linkedin/callback` | Callback LinkedIn OAuth |

### Vagas
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/jobs` | Buscar vagas locais |
| GET | `/jobs/remoteok` | RemoteOK |
| GET | `/jobs/indeed` | Indeed |
| GET | `/jobs/linkedin` | LinkedIn Jobs |
| GET | `/jobs/gupy` | Gupy |
| GET | `/jobs/programathor` | Programathor |
| GET | `/jobs/geekhunter` | GeekHunter |
| GET | `/jobs/{id}` | Detalhes de uma vaga |

### IA
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/ai/match` | Matching currículo vs vaga |
| POST | `/ai/ats-score` | ATS Score |
| POST | `/ai/cover-letter` | Gerar carta de apresentação |
| POST | `/ai/tailor-resume` | Gerar currículo personalizado |
| POST | `/ai/auto-apply` | Candidatura automática (currículo + carta + aplicação) |
| POST | `/ai/chat` | Chat assistente de carreira |
| POST | `/ai/linkedin/analyze` | Análise de perfil LinkedIn |
| POST | `/ai/github/import` | Importar dados do GitHub |

### Analytics
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/analytics/overview` | KPIs, top empresas, top skills, timeline |

### Busca Semântica
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/search/semantic` | Busca por similaridade (embeddings) |
| POST | `/search/index-job/{id}` | Indexar vaga para busca semântica |

### Candidaturas
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/applications` | Registrar candidatura |
| GET | `/applications/list` | Listar candidaturas |
| GET | `/applications/stats` | Estatísticas |
| PATCH | `/applications/{id}/status` | Atualizar status |

### Notificações
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/notifications` | Listar notificações |
| GET | `/notifications/unread-count` | Contagem de não lidas |
| PATCH | `/notifications/{id}/read` | Marcar como lida |

### Currículos
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/resumes/upload` | Upload PDF |
| GET | `/resumes/list` | Listar |
| GET | `/resumes/{id}` | Detalhes |

---

## 🧠 Arquitetura de IA — Strategy Pattern

```
┌────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│   LLMService   │────▶│  LLMProvider     │◀────│  OpenAIProvider   │
│  (Application) │     │   (Domain)       │     ├───────────────────┤
│                │     │                  │────▶│ AnthropicProvider │
│ - generate     │     │ - analyze_resume │     ├───────────────────┤
│ - summarize    │     │ - compare_job    │────▶│  GeminiProvider   │
│ - analyze      │     │ - cover_letter   │     ├───────────────────┤
│ - compare      │     │ - tailored_resume│────▶│  OllamaProvider   │
│ - cover_letter │     │ - health_check   │     ├───────────────────┤
│ - tailor_resume│     └──────────────────┘     │ NVIDIA NIM        │
└────────────────┘                              ├───────────────────┤
        ┌──────────────┐                        │ OpenRouter        │
        │   Factory    │                        └───────────────────┘
        │ (Cria provider│
        │  baseado na   │
        │  configuração │
        │  do usuário)  │
        └──────────────┘
```

- Chaves de API criptografadas com **Fernet** no banco
- Resultados cacheados no **Redis** (1h TTL)
- 6 provedores: OpenAI, Anthropic, Gemini, Ollama, NVIDIA NIM, OpenRouter

---

## 📊 Banco de Dados

20 tabelas principais — PostgreSQL 16 com extensão **pgvector** para busca semântica.

Migrações: `cd apps/backend && alembic upgrade head`

---

## 🐳 Serviços Docker

| Serviço | Porta | Descrição |
|---------|-------|-----------|
| `postgres` | 5432 | PostgreSQL + pgvector |
| `redis` | 6379 | Cache + Celery broker |
| `backend` | 8000 | FastAPI (uvicorn) |
| `celery-worker` | — | Workers assíncronos |
| `celery-beat` | — | Tarefas agendadas |
| `frontend` | 3000 | Next.js |

> Em **desenvolvimento** o nginx foi removido: backend expõe `:8000` e frontend `:3000` diretamente.
> Em **produção** use o reverse proxy (config em `infra/docker/nginx/`).

---

## 🧪 Testes — 47 testes passando

```bash
cd apps/backend
pip install -r tests/requirements-test.txt  # ou: pip install pytest pytest-asyncio httpx aiosqlite numpy
PYTHONPATH=src pytest tests/ -v
```

| Teste | Qtd | O que cobre |
|-------|-----|-------------|
| `test_auth.py` | 6 | Register, login, logout, me, duplicate, wrong password |
| `test_analytics.py` | 2 | Overview vazio + com dados |
| `test_search.py` | 3 | Busca semântica, index, not found |
| `test_ai.py` | 7 | Tailor resume, auto apply, matching, ATS, cover letter |
| `test_notifications.py` | 7 | CRUD + providers (email, discord, telegram) |
| `test_oauth.py` | 3 | LinkedIn login, callback, state inválido |
| `test_infrastructure.py` | 7 | Embeddings, cosine similarity |
| `test_models.py` | 2 | User, Job |
| `test_modules.py` | 6 | Calendar CRUD, chat, GitHub, LinkedIn, full flow |
| `test_applications.py` | 2 | Create + list |
| `test_health.py` | 1 | Health check |

---

## 🚢 Deploy

### Coolify
Guia completo em `infra/coolify/README.md`

```bash
cp infra/coolify/.env.production.example .env.production
# Preencha as variáveis
# Cole o docker-compose.prod.yml no Coolify
```

### Railway
Guia completo em `infra/railway/README.md`

---

## 📄 Licença

MIT

---

**Feito com dedicação por [Lucas Oliver](https://github.com/blackxzin)**
