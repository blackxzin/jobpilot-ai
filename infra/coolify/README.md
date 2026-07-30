# Deploy JobPilot AI no Coolify

## Pré-requisitos

1. Coolify instalado e rodando (ou Coolify Cloud)
2. Domínio configurado apontando pro servidor
3. Docker + Compose disponível

## Passo a Passo

### 1. Criar arquivo de ambiente

```bash
cp infra/coolify/.env.production.example .env.production
# Editar com suas chaves reais
nano .env.production
```

Campos obrigatórios:
- `APP_SECRET_KEY` — gere com `openssl rand -base64 32`
- `POSTGRES_PASSWORD` — senha forte pro banco
- Pelo menos uma chave de LLM (`OPENAI_API_KEY` ou similar)
- `DOMAIN` — seu domínio (ex: `jobpilot.seusite.com`)

### 2. No Coolify

**Opção A — Docker Compose (recomendado):**

1. Clique em **New Resource** → **Docker Compose**
2. Cole o conteúdo de `infra/coolify/docker-compose.prod.yml`
3. Adicione as variáveis de ambiente do `.env.production`
4. Configure o domínio em **Domains** (nginx porta 80/443)
5. Deploy!

**Opção B — Serviço único (Coolify Private Registry):**

1. Backend: New Resource → Private Docker Image
   - Build pack: `Dockerfile`
   - Root location: `/apps/backend`
   - Port: `8000`
2. Frontend: New Resource → Private Docker Image
   - Build pack: `Dockerfile`
   - Root location: `/apps/frontend`
   - Port: `3000`
3. PostgreSQL + Redis: New Resource → Database

### 3. SSL/HTTPS

- Coolify cuida do SSL automaticamente via Let's Encrypt
- Ou coloque seus certificados em `infra/docker/nginx/ssl/`

### 4. Verificar

```bash
curl https://seu-dominio/health
# {"status": "healthy", "version": "0.1.0", "environment": "production"}
```

## Railway

### Deploy no Railway

1. Conecte o repositório GitHub ao Railway
2. Railway detecta `docker-compose.yml` automaticamente
3. Configure as variáveis de ambiente no dashboard
4. Railway cuida de SSL, domínio e banco PostgreSQL

Dica: Use `railway.toml` ou o dashboard pra configurar serviços separados
(backend porta 8000, frontend porta 3000, nginx porta 80).
