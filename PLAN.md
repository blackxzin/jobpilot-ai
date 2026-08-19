# JobPilot AI — Status do Projeto

> **Status:** 🟢 MVP Completo | **Versão:** 1.1 — Agosto 2026

---

## 🔧 Auditoria e correções — Agosto 2026

Revisão completa do projeto (backend, frontend, infra) para deixá-lo 100% funcional. Bugs corrigidos:

**Segurança**
- Senhas eram hash SHA-256 sem salt — trocado por PBKDF2-HMAC-SHA256 (600k iterações) com salt aleatório; hashes legados continuam autenticando e são migrados automaticamente no próximo login.
- IDOR em `applications`, `resumes`, `notifications`, `calendar`: qualquer usuário logado podia ler/editar dados de outro usuário pelo ID. Agora toda rota valida posse do recurso (404 se não for dono).
- Estado do OAuth do LinkedIn nunca expirava e crescia sem limite; agora expira em 10 min e tem teto de entradas pendentes. Login sem `LINKEDIN_CLIENT_ID`/`SECRET` configurados agora retorna 503 em vez de gerar uma URL quebrada.
- `FRONTEND_URL` do redirect pós-OAuth não era mais hardcoded para localhost.

**Bugs que quebravam funcionalidades**
- `job.company` (nome da empresa) lia uma relação lazy dentro de uma rota async → `MissingGreenlet` e HTTP 500 em Match, ATS Score, Carta de Apresentação, Currículo Inteligente e Auto Apply. Corrigido com eager-load (`selectinload`).
- Import do GitHub usava o endpoint `/user/repos` (repos do token autenticado) em vez de `/users/{username}/repos` — nunca trazia os repositórios da pessoa pesquisada.
- Embedding fallback (busca semântica) reinterpretava bytes de hash como float32 crus, gerando `inf`/`NaN` e resultados de similaridade quebrados. Trocado por PRNG determinístico normalizado.
- `lifespan` do FastAPI nunca era passado para `FastAPI(...)` — as tabelas nunca eram criadas automaticamente no start em dev.
- Chamadas ao LLM não tinham timeout — uma API fora do ar travava a requisição (e o worker HTTP) indefinidamente. Agora todo provedor tem timeout configurável (`LLM_TIMEOUT_SECONDS`, padrão 60s) e falhas retornam 502 em vez de travar ou dar 500.
- Notificações por e-mail enviavam o **UUID do usuário** como destinatário para a Resend em vez do e-mail — todo envio falhava silenciosamente.
- IDs inválidos (UUID malformado, status inexistente, data malformada) causavam 500 em vez de 422 em várias rotas.
- `docker-compose.yml` mapeava as portas 5432/6379/8000/3000 fixas no host, causando conflito quando já havia outro Postgres/Redis local — agora configuráveis via `POSTGRES_HOST_PORT` etc. (padrão evita colisão).
- `init.sql` falhava o boot do Postgres se a extensão `vector` não existisse na imagem usada.
- Sessão do frontend não persistia — qualquer F5 derrubava o login.
- ESLint quebrado (config antiga v8 num pacote com ESLint v9); adicionado `eslint.config.js` flat.
- Criada a primeira migration Alembic real (schema estava sem nenhuma revisão versionada).
- `numpy` era usado mas não estava em `requirements.txt`.
- Diversos `except: pass` silenciosos, imports não usados, comparações `== True`, e outros itens de lint (ruff agora limpo em `src/` e `tests/`).

**Verificação feita**
- Suíte de testes: 57 passed, 4 skipped (chave de LLM opcional) — inclui `test_regressions.py`, novo, cobrindo os bugs acima.
- Stack completa validada via `docker compose up`: postgres, redis, backend, frontend, celery-worker, celery-beat sobem e o frontend fala com o backend via proxy.
- Build de produção do frontend (`next build`) e `tsc --noEmit` passam sem erros.

---

## ✅ O QUE ESTÁ PRONTO

### Backend (FastAPI + Python)

| Módulo | Status | O que faz |
|--------|--------|-----------|
| 🔐 **Auth** | ✅ Completo | Register, login, logout, sessão com tokens, proteção de rotas |
| 👤 **Users** | ✅ Completo | Perfil de usuário, proteção por token |
| 💼 **Jobs** | ✅ Completo | Busca local + integração com 6 fontes + busca semântica pgvector |
| 🤖 **AI / LLM** | ✅ Completo | 6 provedores: OpenAI, Anthropic, Gemini, NVIDIA NIM, Ollama, OpenRouter — tailored resume + auto apply. **Default/dev:** NVIDIA NIM (`meta/llama-3.2-3b-instruct`) via chave OpenAI-compatible em `OPENAI_API_KEY` |
| 📄 **Resume** | ✅ Completo | Upload de PDF, extração de texto com pypdf |
| 📋 **Applications** | ✅ Completo | Pipeline com status, CRUD completo |
| ✉️ **Cover Letters** | ✅ Completo | Geração automática com IA |
| 📅 **Calendar** | ✅ Completo | Agenda de entrevistas, CRUD com status |
| 💬 **Chat** | ✅ Completo | Assistente de carreira com IA |
| 🐙 **GitHub Import** | ✅ Completo | Importa perfil, repositórios e skills via API |
| 🔗 **LinkedIn Analysis** | ✅ Completo | Análise de perfil via IA |
| 📊 **Matching + ATS** | ✅ Completo | Score de compatibilidade e análise de currículo vs vaga |
| 📊 **Analytics** | ✅ Completo | Taxa de entrevista/oferta/rejeição, top empresas, top skills, timeline |
| 🔔 **Notifications** | ✅ Completo | Email (Resend), Discord webhook, Telegram bot |
| ⚡ **Celery Workers** | ✅ Completo | Tasks assíncronas: scraping, matching, ATS, email |

### Frontend (Next.js + React + Tailwind)

| Tela | Status | Funcionalidades |
|------|--------|----------------|
| **Login** | ✅ | Email/senha, entrada rápida, login com LinkedIn OAuth |
| **Dashboard** | ✅ | KPIs (taxa entrevista/oferta/rejeição), top empresas, top skills, timeline 30d, GitHub Import, LinkedIn Analysis |
| **Jobs** | ✅ | Busca em 6 fontes + busca semântica, filtros (Estágio, Jr, Pleno, Senior, CLT, PJ...) |
| **Calendar** | ✅ | Criar/editar/deletar eventos de entrevista |
| **Applications** | ✅ | Pipeline de status + botões Matching, ATS Score, Carta, Currículo Inteligente, Auto Apply |
| **Notifications** | ✅ | Dropdown na navbar com contador, marca como lida |
| **Resumes** | ✅ | Upload PDF, listagem |
| **Chat** | ✅ | Assistente de carreira IA |
| **IA Settings** | ✅ | Configurar chave dos 6 provedores |

### Infraestrutura

| Item | Status |
|------|--------|
| 🐳 Docker Compose (PostgreSQL, Redis, Backend, Frontend, Celery) | ✅ | Nginx removido em dev — backend expõe :8000 e frontend :3000 diretamente |
| 🗄️ 18 tabelas SQLAlchemy | ✅ |
| 🧪 47 testes passando | ✅ | auth, analytics, search, notifications, ai, oauth, models, calendar, infra |
| 📝 README completo | ✅ |
| 🚀 CI/CD com GitHub Actions | ✅ |
| 🔒 Chaves de API criptografadas | ✅ |

---

---

## ❌ AINDA NÃO FEITO

| Prioridade | Funcionalidade | Esforço |
|-----------|----------------|---------|
| — | 📱 **PWA** — transformar em Progressive Web App | 🟡 1 dia |

---

## 📊 COMPARATIVO COM O PLANO ORIGINAL

### MVP Original (Fase 0 + Fase 1)

| Requisito | Status |
|-----------|--------|
| ✅ Auth completo | ✅ |
| ✅ CRUD de perfil | ✅ |
| ✅ Upload + parsing PDF | ✅ |
| ✅ 3+ provedores LLM | ✅ (6 provedores) |
| ✅ Buscador de vagas (2+ fontes) | ✅ (4 fontes) |
| ✅ Matching com score | ✅ |
| ✅ ATS Score | ✅ |
| ✅ Geração de cover letter | ✅ |
| ✅ Rastreamento de candidaturas | ✅ |

### Extras que já foram feitos (não estavam no MVP)

| Extra | Status |
|-------|--------|
| Chat assistente IA | ✅ |
| Agenda de entrevistas | ✅ |
| Importar GitHub | ✅ |
| Analisar LinkedIn | ✅ |
| Gráfico no Dashboard | ✅ |
| 16 testes automatizados | ✅ |
| NVIDIA NIM como provedor default (dev) | ✅ | `meta/llama-3.2-3b-instruct` com chave OpenAI-compatible |

---

## 🚀 PRÓXIMOS PASSOS RECOMENDADOS

Maior impacto com menor esforço:

1. 🌐 **Login LinkedIn OAuth** — criar app no LinkedIn Developers
2. 🚀 **Deploy** — subir em produção com Coolify
3. 🔄 **Indeed + mais fontes de vaga**
4. 🤖 **Automação de candidaturas**
5. 📱 **PWA** — transformar em Progressive Web App

---

*Gerado em: Julho 2026*
*Repositório: [github.com/blackxzin/JOBPILOT_AI](https://github.com/blackxzin/JOBPILOT_AI)*
