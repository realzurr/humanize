# Handoff — Continuação pós-Onda 8

> Documento de continuidade. Permite a qualquer agente retomar o trabalho de
> onde parou, com o estado atual, o backlog priorizado e os passos técnicos
> detalhados da tarefa em andamento.
>
> **Última atualização**: 2026-10-22
> **Estado**: todas as 8 ondas concluídas + resolução dos 9 GAPs da auditoria
> de QA. Trabalho em andamento abaixo.

---

## 1. Estado atual (contexto)

- **Backend** (FastAPI + SQLAlchemy 2.0 + Alembic): normalização, multi-LLM,
  humanização + validador semântico, templates ABNT, referências (NBR 6023/10520),
  exportação (DOCX/PDF/TXT/MD), persistência relacional, autenticação **opt-in**
  (`auth_enabled`), uploads seguros, rate limiting, credenciais AES-GCM.
- **Frontend** (React 18 + TS + Vite + Tailwind): 11 páginas, editor comparativo,
  estado de documento em memória (`DocumentoContext`), testes Vitest + Playwright.
- **Qualidade**: `ruff`/`mypy`/`pytest` (540 testes + 1 opcional de Redis real, cobertura 96%) verdes;
  frontend `lint`/`typecheck`/`build`/`test`/`test:e2e` verdes.
- **Auth**: backend implementa `/auth/register`, `/auth/token`, `/auth/me` e
  dependência `get_current_user` (opt-in). O frontend tem login/registro, token
  em memória, logout com revogação e tratamento de 401.

---

## 2. Backlog priorizado (intenções pendentes)

| # | Item | Prioridade | Status |
|---|---|---|---|
| 1 | **Login/registro no frontend** + token em memória + header `Authorization` | Crítica | ✅ concluído |
| 2 | Validação de configuração no startup (auth/encryption footguns) | Alta | ✅ concluído |
| 3 | Persistir `exports` no ORM (`ExportRepository` + fallback em `/exports`) | Alta | ✅ concluído |
| 4 | Rate limit compartilhado (`sqlite` mesmo host; `redis` multi-nó com Lua atômico — `ADR-0018`) | Média | ✅ concluído |
| 5 | Rotação de `SECRET_KEY`/`ENCRYPTION_KEY` + invalidação de tokens (revogação persistida no banco — `ADR-0018`) | Média | ✅ concluído |
| 6 | Cabeçalhos de segurança (CSP/HSTS/X-Content-Type-Options) no Nginx (`nginx.conf` e `DEPLOYMENT.md`) | Média | ✅ concluído |
| 7 | Rotina agendada e unificada de retenção (`run_retention_sweep` + `retention_sweep_interval_seconds`) | Média | ✅ concluído |
| 8 | Migração de senha PBKDF2 → Argon2id (com rehash automático transparente no login) | Baixa | ✅ concluído |
| 9 | Inspetor estrutural nativo de PDF (`_inspecionar_pdf_nativo` sem depender de `pymupdf`/AGPL) | Baixa | ✅ concluído |
| 10 | Config footgun `BEHIND_PROXY` em produção (documentado e validado no startup) | Média | ✅ concluído |
| 11 | Correções da revisão técnica (`docs/REVISAO_AJUSTES.md`, A1–A16) | Alta | ✅ concluído — ver `docs/waves/onda-8-correcoes.md` |
| 12 | Indireção de chaves de LLM por cofre (`*_API_KEY_ENV_NAME`) | Média | ✅ concluído — `ADR-0018` |
| 13 | Teste dos cabeçalhos do Nginx + execução do e2e | Baixa | ✅ concluído — ver `docs/waves/onda-8-pendencias.md` |
| 14 | `*_API_KEY_FILE`, `POST /auth/logout-all`, Redis no compose, `Cache-Control` único | Baixa | ✅ concluído — `ADR-0019`, `docs/waves/onda-8-pendencias-2.md` |
| 15 | Papel administrativo (revogar/desativar terceiros) | Média | ⏸ aguarda decisão do responsável |

---

## 3. Tarefas concluídas nesta etapa

1. **Autenticação no frontend**:
   - Tipos de autenticação em `frontend/src/types/index.ts`.
   - `definirToken` (somente em memória) + métodos `registrar`, `entrar` e `me` em `frontend/src/services/api.ts`.
   - `AuthProvider`/`useAuth` em `frontend/src/context/AuthContext.tsx`, registrado em `frontend/src/main.tsx`.
   - Página `frontend/src/pages/Login.tsx` e rota `/login` + ação de sessão no cabeçalho de `frontend/src/App.tsx`.
   - Testes unitários em `frontend/tests/unit/auth.test.tsx`.
2. **Validação de configuração no startup (`backend/app/main.py`)**:
   - `_avisar_configuracao_invalida` emite `logger.warning` para `auth_enabled=true` sem `secret_key`, `credential_encryption_enabled=true` sem `encryption_key` válida, e `environment=production` sem `auth_enabled` ou `behind_proxy`.
3. **Persistência relacional de exportações (`ExportRepository`)**:
   - `backend/app/repositories/exports.py` e integração em `backend/app/api/v1/exports.py`, recuperando metadados e arquivos do banco mesmo após reinício do store em memória.
4. **Hash Argon2id + rotação de chaves + revogação de tokens**:
   - `hash_password` usa Argon2id (`cryptography`) por padrão e `verify_password` mantém retrocompatibilidade com `pbkdf2_sha256`, realizando *rehash* automático no login (`/auth/token`).
   - `TokenService` aceita `previous_keys`, revoga tokens por `jti` (`POST /api/v1/auth/logout`) ou por `subject` (`revoke_subject`).
   - `SecretCipher` aceita `previous_encryption_keys` e expõe `rotate(token)`.
5. **Rate limit compartilhado e retenção agendada**:
   - `SqliteSlidingWindowLimiter` (modo WAL, atômico entre múltiplos workers locais) e `RedisSlidingWindowLimiter` em `backend/app/core/ratelimit.py`.
   - `run_retention_sweep` em `backend/app/main.py` e `prune_expired_uploads` em `backend/app/services/ingestion/upload.py`, com agendamento periódico configurável por `RETENTION_SWEEP_INTERVAL_SECONDS`.
6. **Inspeção nativa de PDF sem AGPL**:
   - `_inspecionar_pdf_nativo` em `backend/app/services/document_export/pdf_builder.py` valida contagem de páginas e `MediaBox` em Python puro quando `pymupdf` não está instalado.

---

## 3.1 Correções pós-revisão (2026-10-22)

A revisão em `docs/REVISAO_AJUSTES.md` apontou que parte dos itens acima estava
incompleta (Redis não conectado, CSV de chaves quebrando o startup, download
sem token, XFF falsificável etc.). Todos os itens A1–A16 foram corrigidos; o
relatório está em `docs/waves/onda-8-correcoes.md` e as decisões em `ADR-0017`.
Nada foi commitado.

## 3.2 Pendências autorizadas (2026-10-22)

Revogação persistida, rate limit Redis, cofre de chaves de LLM e teste do Nginx
implementados (`ADR-0018`, `docs/waves/onda-8-pendencias.md`). **Antes do
deploy: `alembic upgrade head`** (migrações `0002` e `0003`). Nada foi commitado.

## 4. Como continuar (se o trabalho for retomado)

1. Ler este arquivo e `git status`/`git log --oneline -10`.
2. Concluir a seção 3 (ou a tarefa seguinte do backlog da seção 2).
3. Ao terminar cada item, atualizar a coluna "Status" da seção 2 e esta seção.
4. Commitar apenas arquivos intencionais (`onda<N>`/descrição curta, em pt-BR).
