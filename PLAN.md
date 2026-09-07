# JobPilot AI — Estado do projeto

**Versão 1.0 · Setembro 2026**

---

## Auditoria de setembro 2026

Revisão completa do backend, frontend e infraestrutura. O que foi encontrado e corrigido.

### Segurança

| Problema | Correção |
|----------|----------|
| Chave real da NVIDIA commitada em `.env.example` (commits `fd00ba1`, `a4cd27b`) | Removida do arquivo. **A chave está queimada — precisa ser revogada em build.nvidia.com.** Adicionada varredura de segredos no CI |
| Login e registro sem limite de tentativas | Rate limit por IP, com Redis compartilhado entre réplicas e contador local como fallback |
| Produção aceitava subir com `SECRET_KEY` padrão — a mesma que criptografa as chaves de API dos usuários | Boot recusado quando `APP_ENV=production` com segredo padrão, `DEBUG=true` ou `DEMO_MODE=true` |
| Upload de currículo lia o arquivo inteiro na memória antes de checar o tamanho | Leitura em blocos, abortando ao ultrapassar o limite; validação da assinatura do PDF |
| Chamada OAuth do LinkedIn sem timeout | Timeout de 15s |
| Rotas de vagas abertas — proxy livre que queimava o rate limit dos sites de vagas | Sessão exigida em todas |
| `SENTRY_DSN` configurável mas nunca lido | Sentry inicializado quando a variável está preenchida |

### Funcionalidades que não funcionavam

| Problema | Correção |
|----------|----------|
| **Todos os workers Celery eram stubs `TODO`** que só logavam e retornavam, com dois serviços rodando 24/7 sem fazer nada | Implementados de verdade: ingestão de vagas com deduplicação e indexação, matching em lote gravando em `job_matches`, ATS Score, entrega de notificações com retentativa, auto apply |
| `celery-beat` subia sem nenhuma tarefa agendada | Agenda real: ingestão a cada 6h, entrega de notificações a cada 5min |
| **Busca semântica retornava ruído ordenado** — o embedding local semeava um PRNG com o hash do documento inteiro, então a direção do vetor não tinha relação com o texto | Vetorizador de bag-of-words com hashing por termo. Documentos que compartilham vocabulário ficam próximos de verdade |
| Busca semântica carregava todos os embeddings e pontuava em laço Python, com N+1 para buscar cada vaga | Pontuação vetorizada em NumPy e uma única query para os resultados |
| Busca semântica mostrava o UUID da empresa no lugar do nome | Nome da empresa, com `selectinload` |
| Lista de candidaturas devolvia só IDs — a tela mostrava `Job: a1b2c3d4…` | Cargo e empresa via outer join |
| ATS Score isolado comparava o currículo com uma vaga genérica, então todo currículo pontuava perto do piso | Auditoria do próprio documento: competências reconhecíveis, extensão, resultados quantificados, contato extraível, seções |
| Tokenizador colava a pontuação final na palavra, então `"git."` nunca casava com a competência `git` | Pontuação final removida; pontuação interna preservada para `next.js`, `c++`, `react-native` |
| `resumes.ats_score` era lido pelo dashboard mas nunca escrito | Calculado por worker no upload |
| ATS Score, carta e currículo direcionado aceitavam silenciosamente uma vaga inexistente e analisavam contra vazio | 404 |
| Importação do GitHub devolvia `{"error": ...}` com HTTP 200 | 404 com mensagem, sem vazar a exceção interna |
| Cache Redis do LLM implementado e nunca acionado | Usado nas análises de perfil |
| `auto-apply` gerava tudo na rota e ainda enfileirava um worker que refazia o mesmo trabalho | Despacho redundante removido |
| Volume nomeado sobre `alembic/versions` escondia as migrations dentro do container | Volume removido |
| Workers subiam antes do Postgres aceitar conexões | `condition: service_healthy` |
| Health check dizia "healthy" sem tocar em nada | `/health` (liveness) e `/health/ready` (banco + Redis) |
| PDF sem camada de texto era salvo com um placeholder e analisado como documento vazio | Rejeitado com explicação |
| Sem chave de API, toda funcionalidade de IA devolvia 502 | Analisador local como fallback |

### Qualidade

- **Provedores de LLM:** 937 linhas removidas, 226 adicionadas. Os seis adaptadores duplicavam prompts e o parser de JSON; agora implementam só o transporte e herdam o resto. Os três compatíveis com OpenAI compartilham uma base.
- **Frontend:** um componente de 1300 linhas virou 20 arquivos focados (maior: 676). `any` eliminado e a regra `no-explicit-any` ativada.
- **Erros:** o frontend mostrava sucesso e falha no mesmo banner verde. Agora há toasts tipados, e o cliente de API propaga a mensagem do servidor em vez de trocá-la por um texto genérico.
- **Login:** registrava primeiro e caía para login, criando conta a cada e-mail digitado errado. Fluxos separados.
- **Dependências:** `pgvector`, `prometheus-client`, `requests` e `Jinja2` estavam declaradas e não usadas. Dois clientes de vagas sem nenhuma referência foram removidos.
- **Testes:** 89 → 108. Workers saíram de 0% para 82–97% de cobertura.
- **CI:** health check nos serviços, relatório de cobertura, varredura de segredos.

### Verificação

- 108 testes passando, 4 pulados (dependem de chave de LLM opcional).
- `ruff check` limpo em `src/` e `tests/`.
- `tsc --noEmit`, `eslint` e `next build` limpos.
- Stack completa validada com `docker compose up`: os 6 serviços sobem, o backend fica saudável, o frontend conversa com a API, o demo entra e todas as telas renderizam sem erro de console.
- Fluxos exercitados de ponta a ponta sem nenhuma chave de API: demo, busca semântica, compatibilidade, ATS Score, carta, worker de matching gravando no banco.

---

## Estado atual

### Pronto

| Área | Situação |
|------|----------|
| Auth + LinkedIn OAuth | Completo |
| Vagas (local + 8 fontes) | Completo |
| Busca semântica | Completo, funciona offline |
| Currículos (upload, parsing, ATS) | Completo |
| IA (match, ATS, carta, currículo, auto apply, chat) | Completo, com fallback local |
| Candidaturas | Completo |
| Agenda | Completo |
| Analytics | Completo |
| Notificações (e-mail, Discord, Telegram) | Completo |
| Workers Celery + Beat | Completo |
| Modo demonstração | Completo |
| PWA | Completo |
| Docker Compose | Completo |
| CI/CD | Completo |

### Pendências conhecidas

| Item | Observação |
|------|-----------|
| **Revogar a chave da NVIDIA** | Está no histórico público do Git. Removê-la do arquivo não basta |
| Cobertura em 67% | Alvo é 80%. Falta principalmente nos clientes de sites de vagas, que dependem de rede |
| Estado do OAuth em memória | Só funciona com uma réplica do backend. Mover para Redis antes de escalar horizontalmente |
| `search-all` cobre 3 das 8 fontes | As demais exigem chave ou raspagem instável |
| Análise de perfil do LinkedIn | O modelo infere o perfil a partir da URL, sem acessar a página. É um palpite, não um dado |
| Currículo não é armazenado | Só o texto extraído é gravado; `file_url` é um rótulo |

### Próximos passos sugeridos

1. Revogar e rotacionar a chave exposta.
2. Testes E2E no frontend (Playwright já está nas dependências).
3. Mover o estado do OAuth para Redis.
4. Armazenar o PDF original em storage de objetos.
5. Expor os `job_matches` do worker em uma tela de recomendações.
