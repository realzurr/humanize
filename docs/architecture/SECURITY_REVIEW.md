# Revisão de Segurança — Onda 8

> Revisão realizada em **2026-10-22**, na conclusão da Onda 8 (Segurança,
> Testes e Estabilização). Registra o que foi mitigado, o que foi testado e as
> pendências antes de qualquer disponibilização pública. **Não declara
> conformidade integral** — apenas o estado verificado.

---

## 1. Escopo e método

Revisão manual + testes automatizados sobre as superfícies de ataque
introduzidas pelas ondas 1–8. Critérios: autenticação/authorização,
isolamento de dados, manipulação de segredos, uploads, injeção de prompt,
limites de consumo e retenção.

---

## 2. Resultado por área

| # | Área | Mitigação | Testado? | Risco residual |
|---|---|---|---|---|
| 1 | Segredos em log/resposta | `redact_secrets` (`app/core/logging.py`); API só expõe `configured`/`last4` | ✅ `test_logging.py`, `test_provider_credentials.py` | Nenhum crítico conhecido |
| 2 | Hash de senha | PBKDF2-SHA256 (600k iterações, salt por usuário) via `cryptography` | ✅ `test_security.py` | Trocar por Argon2id futuramente |
| 3 | Tokens de acesso | HMAC-SHA256 assinado, com expiração e `jti`; `SECRET_KEY` obrigatória | ✅ `test_security.py`, `test_auth_api.py` | Rotação de chave não implementada |
| 4 | Isolamento por usuário | `owner_id` em documentos/credenciais; `get_current_user` opt-in | ✅ `test_documents_api.py`, `test_persistent_credentials.py` | Modo local (`AUTH_ENABLED=false`) não isola |
| 5 | Credenciais em repouso | AES-GCM (`SecretCipher`), chave fora do banco | ✅ `test_persistent_credentials.py` | Exige `ENCRYPTION_KEY`; sem ela, só sessão |
| 6 | Uploads | Tamanho, magic bytes, nome sanitizado, `is_relative_to`/prefixo | ✅ `test_ingestion.py`, `test_uploads_api.py` | DOCX lido via `python-docx` (entrada não confiável é conteúdo) |
| 7 | Prompt injection | Conteúdo delimitado + instrução de sistema anti-instrução | ✅ `test_humanizer_engine.py` | Heurística; depende também do provedor |
| 8 | Rate limiting | Janela deslizante em memória (login, humanização) | ✅ `test_ratelimit.py`, `test_rate_limit_api.py` | Por processo; usar Redis para múltiplos workers |
| 9 | Retenção/exclusão | `document_retention_days` + `prune_expired` + rotas de exclusão | ✅ `test_documents_repository.py` | Sem rotina agendada automática |
| 10 | CORS/TLS | CORS via `allow_origins`; TLS no proxy | Manual | TLS depende do deploy |

---

## 3. Pendências de segurança (antes de público)

1. **Backend de rate limit compartilhado** (Redis) para múltiplos workers.
2. **Rotação de `SECRET_KEY`/`ENCRYPTION_KEY`** e invalidação de tokens.
3. **Autenticação no frontend** (login/registro + token em memória) — o backend
   é opt-in; a UI da Onda 7 opera em modo local sem login.
4. **Auditoria de dependências** (`npm audit` / `pip-audit`) no CI.
5. **Cabeçalhos de segurança** (CSP, HSTS, X-Content-Type-Options) no proxy.
6. **Rotina agendada de retenção** (cron/scheduler) para documentos e uploads.
7. Migração de PBKDF2-SHA256 para **Argon2id** quando viável.

---

## 4. Conclusão

Nenhuma falha crítica conhecida nas superfícies revisadas. A aplicação está
pronta para **implantação controlada** (staging), não para exposição pública
irrestrita, até que as pendências da seção 3 sejam resolvidas. A conformidade
é declarada **por item verificado**, nunca presumida integralmente.

---

## 5. Adendo — Auditoria de QA (2026-10-22)

Uma auditoria independente de qualidade (`backend/tests/docs/Actions.md`)
confirmou sete bugs/vulnerabilidades reais (GAP-01 a GAP-09). Todos foram
corrigidos no código e cobertos por testes de regressão:

- **GAP-01/02**: isolamento cross-tenant de credenciais + resolução da chave
  persistida pelo `ProviderRegistry.build()`.
- **GAP-03**: autenticação/isolamento por `owner_id` em `/exports`, `/uploads`
  e `/humanize`.
- **GAP-04**: bypass de rate limit via `X-Forwarded-For` (agora exige
  `BEHIND_PROXY=true`).
- **GAP-05**: colisão de nomes e extração DOCX síncrona no upload.
- **GAP-06**: `/health/readiness` com checagem real do banco.
- **GAP-07/08**: testes de fronteira e de cascata ORM.
- **GAP-09**: `pymupdf` tornado opcional (`ADR-0016`).

O status detalhado da resolução está na seção 13 de `backend/tests/docs/Actions.md`.
