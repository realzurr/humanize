# Guia de Implantação (Deployment)

> Documento operacional para colocar o **Humaniza Acadêmico** em produção.
> Complementa `docs/ARCHITECTURE.md` e `docs/DECISIONS.md`. A versão descrita
> corresponde à conclusão da **Onda 8** (segurança e estabilização).

---

## 1. Visão geral

A aplicação tem dois componentes:

1. **Backend** — API FastAPI (Python 3.12), em `backend/`.
2. **Frontend** — SPA React 18 + TypeScript (Vite), em `frontend/`, servida por
   um proxy/estático.

Recomenda-se executá-los atrás de um **proxy reverso** (Nginx/Traefik/Caddy)
com **TLS**. O renderizador de PDF roda em subprocesso isolado (LibreOffice).

---

## 2. Variáveis de ambiente

Copie `backend/.env.example` (ou o `.env.example` da raiz) e preencha. As
variáveis são lidas por `app/core/config.py` (pydantic-settings).

### Obrigatórias em produção

| Variável | Descrição | Exemplo |
|---|---|---|
| `ENVIRONMENT` | `production` | `production` |
| `SECRET_KEY` | Chave de assinatura de tokens de acesso (HMAC). Gere com `secrets.token_urlsafe(48)`. | — |
| `AUTH_ENABLED` | Habilita autenticação e isolamento por usuário. | `true` |
| `DATABASE_URL` | URL SQLAlchemy do banco (PostgreSQL em produção). | `postgresql+psycopg://user:pass@host:5432/humaniza` |
| `ENCRYPTION_KEY` | Chave AES-GCM (32 bytes, base64) para credenciais persistidas. | `python -c "import base64,os;print(base64.b64encode(os.urandom(32)).decode())"` |
| `CREDENTIAL_ENCRYPTION_ENABLED` | Grava credenciais cifradas no banco. | `true` |
| `BEHIND_PROXY` | Habilita leitura de `X-Forwarded-For` pelo rate limiter atrás do proxy reverso. | `true` |

### Opcionais

| Variável | Padrão | Descrição |
|---|---|---|
| `ACCESS_TOKEN_TTL_SECONDS` | `3600` | Validade do token de acesso. |
| `RATE_LIMIT_LOGIN_PER_MINUTE` | `10` | Limite de tentativas de login (por IP). |
| `RATE_LIMIT_HUMANIZE_PER_MINUTE` | `30` | Limite de humanizações (por IP). |
| `RATE_LIMIT_BACKEND` | `memory` | `memory` (por processo) \| `sqlite` (workers do mesmo host, em `STORAGE_DIR/ratelimit.db`) \| `redis` (vários nós; exige `REDIS_URL` e o extra `redis`). |
| `REDIS_URL` | vazio | Ex.: `redis://redis:6379/0`. Obrigatória com `RATE_LIMIT_BACKEND=redis`. |
| `REVOCATION_BACKEND` | `database` | Revogação de tokens: `database` (compartilhada e persistente) \| `memory` (por processo). |
| `<PROVEDOR>_API_KEY_ENV_NAME` | vazio | Nome da variável em que o cofre injeta a chave de LLM (OpenAI, Anthropic, Gemini, compatível). |
| `<PROVEDOR>_API_KEY_FILE` | vazio | Caminho absoluto de arquivo com a chave (ex.: `/run/secrets/openai_api_key`). Precedência: `*_API_KEY` > `*_ENV_NAME` > `*_FILE`. |
| `TRUSTED_PROXY_HOPS` | `1` | Nº de proxies confiáveis que anexam ao `X-Forwarded-For` (só com `BEHIND_PROXY=true`). |
| `DOCUMENT_RETENTION_DAYS` | `30` | Prazo de retenção de documentos/exportações. |
| `RETENTION_SWEEP_INTERVAL_SECONDS` | `0` | Intervalo da varredura automática de retenção (documentos, exportações e uploads); `0` desliga. |
| `PREVIOUS_SECRET_KEYS` | vazio | Chaves de assinatura anteriores (CSV ou lista JSON) aceitas durante a rotação. |
| `PREVIOUS_ENCRYPTION_KEYS` | vazio | Chaves AES-GCM anteriores (CSV ou lista JSON) aceitas na decifragem durante a rotação. |
| `MAX_UPLOAD_BYTES` | `10485760` | Tamanho máximo de upload (10 MiB). |
| `PDF_RENDERER` | `libreoffice` | `libreoffice` \| `docx2pdf` \| `none`. |
| `LIBREOFFICE_BINARY` | `soffice` | Caminho do binário do LibreOffice. |
| `CORS_ORIGINS` | `http://localhost:5173` | Origens permitidas (CSV). |

> **Nunca** versione `.env` nem escreva chaves reais em código, fixtures ou
> logs. Em produção, use um cofre de segredos (Vault, AWS Secrets Manager,
> env do orquestrador) em vez do arquivo `.env`.

---

## 3. Migrações de banco

O esquema é gerenciado por **Alembic** (`backend/alembic/`). Em produção, as
tabelas **nunca** são criadas por `create_all`.

```bash
cd backend
# Aplicar migrações
alembic upgrade head

# Gerar nova migração após mudar os modelos
alembic revision --autogenerate -m "descrição"

# Retroceder
alembic downgrade -1
```

A URL de banco usada pelo Alembic é lida de `app.core.config.Settings`
(variável `DATABASE_URL`), nunca hard-coded. O motor da aplicação também usa
essa URL.

### PostgreSQL

Instale o driver `psycopg` e ajuste `DATABASE_URL`:

```bash
uv pip install psycopg[binary]
```

---

## 4. Proxy reverso e TLS

Exemplo com Nginx (terminação TLS):

```nginx
server {
    listen 443 ssl http2;
    server_name humaniza.exemplo.org;

    ssl_certificate     /etc/ssl/humaniza/fullchain.pem;
    ssl_certificate_key /etc/ssl/humaniza/privkey.pem;

    # Cabeçalhos de segurança
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self';" always;

    # Frontend estático + API na mesma origem
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        root /srv/humaniza/frontend/dist;
        try_files $uri /index.html;
    }
}
```

> **Nginx e `add_header`:** um `add_header` declarado dentro de um `location`
> descarta todos os herdados do `server`. Se algum bloco precisar de cabeçalho
> próprio (ex.: `Cache-Control` em `/assets/`), repita nele os cabeçalhos de
> segurança — como faz `frontend/nginx.conf`.

- **TLS**: use Let's Encrypt (`certbot`) ou o TLS do orquestrador.
- Defina `BEHIND_PROXY=true` no backend quando operando atrás do Nginx para que o rate limiter utilize o `X-Forwarded-For` real de cada cliente (sem isso, todos os usuários compartilharão o IP do proxy). Se a API estiver exposta diretamente sem proxy confiável, mantenha `BEHIND_PROXY=false` para impedir falsificação de IP.
- `$proxy_add_x_forwarded_for` **anexa** o IP visto pelo proxy ao valor enviado pelo cliente; as entradas à esquerda são falsificáveis. O backend usa a entrada na posição `-TRUSTED_PROXY_HOPS`: com um único Nginx, `1`; com Nginx TLS na frente do Nginx do contêiner do frontend, `2`.
- Sirva o build do frontend (`npm run build` → `frontend/dist`) como estático.

---

## 5. Execução

### Backend

```bash
cd backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

> Para múltiplos workers, use um banco compartilhado (PostgreSQL) e
> `RATE_LIMIT_BACKEND=sqlite` (mesmo host) ou `redis` (vários nós:
> `uv pip install -e ".[redis]"` + `REDIS_URL`). A revogação de tokens
> (`/auth/logout`) fica no banco por padrão (`REVOCATION_BACKEND=database`) e é
> compartilhada entre workers e nós. Rode `alembic upgrade head` antes do deploy.

### Frontend

```bash
cd frontend
npm ci
npm run build   # gera frontend/dist
```

O `frontend/nginx.conf` e o `frontend/Dockerfile` já estão prontos para o
deploy em contêiner (multi-stage: build do Node → serve com Nginx).

### Docker Compose

Para testar o rate limit com Redis localmente:

```bash
BACKEND_EXTRAS=redis RATE_LIMIT_BACKEND=redis \
  docker compose --profile app --profile redis up --build
```

O argumento de build `EXTRAS` do `backend/Dockerfile` instala extras opcionais
(`redis`, `pdf`).

O `docker-compose.yml` na raiz orquestra backend + frontend + banco. Ajuste as
variáveis de ambiente e as credenciais do banco antes de subir.

---

## 6. Backup e retenção

| Artefato | Onde | Retenção |
|---|---|---|
| Banco (documentos, usuários, credenciais, exportações) | `DATABASE_URL` | Backups regulares do PostgreSQL |
| Arquivos exportados (DOCX/PDF/TXT/MD) | `EXPORT_DIR` (padrão `backend/data/exports`) | `DOCUMENT_RETENTION_DAYS` |
| Uploads | `STORAGE_DIR/uploads` | Limpar via rotina de retenção |

- **Backup**: faça dump do PostgreSQL (`pg_dump`) com periodicidade compatível
  com a política da instituição; teste a restauração periodicamente.
- **Retenção**: `POST /api/v1/documents/prune` remove documentos e exportações
  expirados do usuário (linha no banco e arquivo em `EXPORT_DIR`). Com
  `RETENTION_SWEEP_INTERVAL_SECONDS > 0`, cada worker executa a varredura
  completa (`run_retention_sweep`: documentos, exportações e uploads de todos os
  usuários) periodicamente; falhas são registradas em log e a rotina continua.

---

## 7. Operação do renderizador de PDF

O PDF é renderizado a partir do DOCX em subprocesso isolado:

- **Requisito**: `soffice` (LibreOffice) instalado e acessível no `PATH` ou no
  caminho de `LIBREOFFICE_BINARY`.
- Executa `soffice --headless --convert-to pdf` com perfil isolado
  (`-env:UserInstallation`), fora do event loop (`asyncio.to_thread`).
- Sem LibreOffice disponível, defina `PDF_RENDERER=none`: a API declara a
  limitação e entrega apenas DOCX/TXT/Markdown.
- Diferenças entre PDF (LibreOffice) e DOCX (Word) estão documentadas em
  `docs/architecture/PDF_RENDERER_NOTES.md`.

```bash
# Ubuntu/Debian
apt-get install -y libreoffice-writer libreoffice-core fonts-liberation
```

---

## 8. Checklist de produção

- [ ] `ENVIRONMENT=production`, `AUTH_ENABLED=true`, `SECRET_KEY` e `ENCRYPTION_KEY` definidos via cofre.
- [ ] `DATABASE_URL` apontando para PostgreSQL e `alembic upgrade head` aplicado.
- [ ] TLS habilitado no proxy; HTTP redireciona para HTTPS.
- [ ] Backups agendados e testados; política de retenção configurada.
- [ ] LibreOffice instalado (ou `PDF_RENDERER=none` declarado).
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` verdes.
- [ ] Revisão de segurança registrada (`docs/architecture/SECURITY_REVIEW.md`).
