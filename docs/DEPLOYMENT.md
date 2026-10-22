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

### Opcionais

| Variável | Padrão | Descrição |
|---|---|---|
| `ACCESS_TOKEN_TTL_SECONDS` | `3600` | Validade do token de acesso. |
| `RATE_LIMIT_LOGIN_PER_MINUTE` | `10` | Limite de tentativas de login (por IP). |
| `RATE_LIMIT_HUMANIZE_PER_MINUTE` | `30` | Limite de humanizações (por IP). |
| `DOCUMENT_RETENTION_DAYS` | `30` | Prazo de retenção de documentos/exportações. |
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

- **TLS**: use Let's Encrypt (`certbot`) ou o TLS do orquestrador.
- O rate limiter considera o `X-Forwarded-For` para identificar o IP real.
- Sirva o build do frontend (`npm run build` → `frontend/dist`) como estático.

---

## 5. Execução

### Backend

```bash
cd backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

> Para múltiplos workers, use um banco compartilhado (PostgreSQL). O rate
> limiter em memória é por processo; para limite global use um backend Redis
> (pendência documentada na revisão de segurança).

### Frontend

```bash
cd frontend
npm ci
npm run build   # gera frontend/dist
```

O `frontend/nginx.conf` e o `frontend/Dockerfile` já estão prontos para o
deploy em contêiner (multi-stage: build do Node → serve com Nginx).

### Docker Compose

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
- **Retenção**: `POST /api/v1/documents/prune` remove documentos expirados do
  usuário; as exportações expiradas são removidas pelo `ExportHistoryStore`
  (`prune_expired`). Considere uma rotina agendada (cron/scheduler).

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
