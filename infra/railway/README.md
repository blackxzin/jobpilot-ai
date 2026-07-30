# Deploy JobPilot AI no Railway

## Pré-requisitos

1. Conta no [Railway](https://railway.app)
2. Repositório GitHub conectado
3. Domínio (opcional — Railway fornece domínio .railway.app)

## Deploy Automático

1. **Crie um novo projeto** no Railway
2. **Conecte** o repositório GitHub
3. Railway detecta o `docker-compose.yml` na raiz e sugere os serviços
4. Configure **cada serviço**:

### Serviços

| Serviço | Porta | Build | Observação |
|---------|-------|-------|------------|
| **postgres** | 5432 | Imagem Docker | Use o PostgreSQL do Railway (Add Database) |
| **redis** | 6379 | Imagem Docker | Railway não tem Redis nativo, manter container |
| **backend** | 8000 | Dockerfile (`apps/backend/Dockerfile`, target=production) | Adicionar env vars |
| **celery-worker** | — | Dockerfile (mesmo do backend) | Comando: `celery worker` |
| **frontend** | 3000 | Dockerfile (`apps/frontend/Dockerfile`, target=production) | Adicionar env vars |
| **nginx** | 80/443 | Imagem Docker | Opcional (Railway cuida de HTTPS) |

### Variáveis de Ambiente (Railway Variables)

Adicione no projeto Railway (Settings → Variables):

```
APP_ENV=production
DEBUG=false
POSTGRES_HOST=<railway-postgres-host>
POSTGRES_PASSWORD=<railway-postgres-password>
DATABASE_URL=<railway-postgres-url>
REDIS_URL=redis://redis:6379/0
APP_SECRET_KEY=<openssl rand -base64 32>
OPENAI_API_KEY=sk-...
EMAIL_API_KEY=re_...
```

### Dica: Sem Nginx no Railway

O Railway gerencia SSL automaticamente. Você pode pular o serviço nginx e
expor backend (:8000) e frontend (:3000) separadamente com domínios diferentes,
ou usar o **domínio personalizado** do Railway apontando pro frontend.

### Verificar

```
curl https://seu-projeto.railway.app/health
```
