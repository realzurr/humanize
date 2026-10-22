# Onda 8 — Segurança, Testes e Estabilização

- **Data**: 2026-10-22
- **Escopo**: persistência relacional (SQLAlchemy 2.0 + Alembic), autenticação
  e autorização opt-in com isolamento por usuário, uploads seguros, rate
  limiting, persistência cifrada (AES-GCM) e gestão de credenciais, retenção e
  exclusão de documentos, proteção contra prompt injection, e documentação de
  implantação e revisão de segurança.
- **Status**: concluída.

---

## 1. Escopo executado

| # | Entregável do ROADMAP | Onde | Estado |
|---|---|---|---|
| 1 | Persistência relacional + migrações | `app/core/database.py`, `app/models/`, `app/repositories/`, `alembic/` | ✅ |
| 2 | Autenticação e autorização | `app/core/security.py`, `app/api/deps.py`, `app/api/v1/auth.py` | ✅ |
| 3 | Isolamento por usuário (`owner_id`) | `app/api/deps.py`, `app/repositories/{documents,credentials}.py` | ✅ |
| 4 | Uploads seguros | `app/api/v1/uploads.py`, `app/services/ingestion/upload.py` | ✅ |
| 5 | Limites de consumo de API | `app/core/ratelimit.py`, `app/api/deps.py` | ✅ |
| 6 | Gestão e exclusão de chaves (AES-GCM) | `app/services/providers/persistent_credentials.py` | ✅ |
| 7 | Retenção e exclusão de documentos | `app/api/v1/documents.py`, `app/repositories/documents.py` | ✅ |
| 8 | Proteção contra prompt injection | `app/services/ingestion/guard.py`, `humanizer/engine.py` | ✅ |
| 9 | Documentação de implantação | `docs/DEPLOYMENT.md` | ✅ |
| 10 | Revisão de segurança registrada | `docs/architecture/SECURITY_REVIEW.md` | ✅ |

## 2. Funcionalidades concluídas

- **Camada de persistência** (antes inexistente): `Base` declarativa, motor e
  fábrica de sessões (`app/core/database.py`), modelos `User`, `Document`,
  `DocumentRevision`, `ProviderCredential`, `Export` em estilo
  `Mapped[]`/`mapped_column`, repositórios por entidade e migração Alembic
  (`0001_inicial`) verificada (`upgrade`/`downgrade`).
- **Autenticação opt-in** (`Settings.auth_enabled`): senhas PBKDF2-SHA256
  (600k iterações, salt por usuário, verificação em tempo constante) e tokens
  HMAC-SHA256 assinados com expiração e `jti`; rotas `POST /auth/register`,
  `POST /auth/token`, `GET /auth/me`. No modo local, a API continua operando
  sem autenticação (retrocompatível com as ondas anteriores).
- **Isolamento por usuário**: `get_current_user` deriva `owner_id` e isola
  documentos e credenciais; testes provam que um usuário não vê/exclui dados
  de outro.
- **Uploads seguros**: limite de tamanho (`max_upload_bytes`), validação do
  tipo real por magic bytes (textuais UTF-8 e DOCX), sanitização de nome e
  defesa em profundidade contra path traversal (`is_relative_to`/prefixo).
- **Rate limiting**: janela deslizante em memória por IP (respeitando
  `X-Forwarded-For`) aplicada a login e humanização, com erro `429`.
- **Credenciais em repouso**: `PersistentCredentialStore` grava o ciphertext
  AES-GCM (`v1:...`) na tabela `provider_credentials`, isolado por dono,
  expondo apenas `configured`/`last4`.
- **Retenção/exclusão**: rotas de documentos (`POST/GET/DELETE/prune`) e
  `DocumentRepository.prune_expired` baseado em `document_retention_days`.
- **Prompt injection**: o conteúdo importado é delimitado
  (`<<<DOCUMENTO_INICIO/FIM>>>`) e a instrução de sistema orienta o modelo a
  tratá-lo como dado; o envoltório é removido da resposta antes da validação.

## 3. Arquivos criados ou modificados

- **Criados (backend)**:
  `app/core/{database,security,ratelimit}.py`, `app/api/deps.py`,
  `app/api/v1/{auth,uploads,documents}.py`,
  `app/models/{_util,user,credential,document,export}.py` e `__init__.py`,
  `app/repositories/{users,credentials,documents}.py`,
  `app/schemas/{auth,uploads,documents}.py`,
  `app/services/ingestion/{__init__,guard,upload}.py`,
  `app/services/providers/persistent_credentials.py`,
  `alembic.ini`, `alembic/env.py`, `alembic/versions/0001_inicial.py`,
  `tests/unit/{test_security,test_ratelimit,test_ingestion,test_persistent_credentials,test_documents_repository}.py`,
  `tests/integration/{test_auth_api,test_documents_api,test_uploads_api,test_rate_limit_api}.py`.
- **Modificados (backend)**:
  `app/main.py`, `app/api/router.py`, `app/api/v1/{providers,humanize}.py`,
  `app/services/humanizer/engine.py`,
  `app/services/providers/credentials.py`,
  `app/core/{config,errors}.py`, `tests/conftest.py`,
  `tests/unit/test_humanizer_engine.py`.
- **Documentação**:
  `docs/DEPLOYMENT.md`, `docs/architecture/SECURITY_REVIEW.md`,
  `docs/ARCHITECTURE.md` (§8, §10), `docs/ROADMAP.md` (Onda 8), `README.md`,
  `.env.example`, `docs/waves/onda-8.md`.

## 4. Testes realizados

| Suíte | Testes |
|---|---|
| Segurança (hash de senha + tokens) | 7 |
| Rate limiting | 3 |
| Ingestão (guard + uploads) | 9 |
| Credenciais persistentes | 5 |
| Repositório de documentos | 4 |
| API de autenticação | 6 |
| API de documentos | 3 |
| API de uploads | 4 |
| API de rate limit | 1 |
| Prompt injection no motor (adicional) | 1 |
| Subtotal Onda 8 | **43** |
| Ondas 0–7 | 423 |
| **Total** | **466** |

## 5. Resultados obtidos (com saída real dos comandos)

```
$ ruff check .
All checks passed!

$ ruff format --check .
176 files already formatted

$ mypy
Success: no issues found in 114 source files

$ pytest
466 passed in 15.90s

$ pytest --cov=app --cov-report=term-missing
TOTAL  5740  262  95%

$ alembic upgrade head   # e downgrade base
Running upgrade -> 0001_inicial, criação inicial das tabelas (Onda 8)
```

## 6. Pendências

| Pendência | Onda | Observação |
|---|---|---|
| Autenticação no frontend (login/registro + token em memória) | pós-8 | Backend opt-in; UI da Onda 7 opera em modo local sem login |
| Backend de rate limit compartilhado (Redis) para múltiplos workers | pós-8 | Hoje em memória por processo |
| Rotação de `SECRET_KEY`/`ENCRYPTION_KEY` e invalidação de tokens | pós-8 | — |
| Rotina agendada de retenção (cron) para documentos/exportações | pós-8 | `prune` disponível, sem scheduler |
| Cabeçalhos de segurança (CSP/HSTS) e `pip-audit`/`npm audit` no CI | pós-8 | — |
| Migração de PBKDF2 para Argon2id | pós-8 | — |

## 7. Riscos conhecidos

- **Modo local sem isolamento**: com `AUTH_ENABLED=false` (padrão em dev), a
  API opera como nas ondas anteriores (sem usuário). Em produção, `AUTH_ENABLED`
  deve ser `true` — coberto por `DEPLOYMENT.md`.
- **Rate limit em memória**: não é global entre workers; documentado e com
  pendência de Redis.
- **`python-docx` lendo DOCX não confiável**: o texto extraído é tratado como
  conteúdo (nunca instrução), mitigando injeção; o documento original nunca é
  executado.
- **Verificação de senha por PBKDF2**: adequada, mas Argon2id seria preferível
  (pendência registrada).

## 8. Próxima onda recomendada

Nenhuma onda formal restante — as **oito ondas do plano foram concluídas**.
Recomenda-se, como continuidade: autenticação no frontend, backend de rate
limit compartilhado, rotina de retenção e endurecimento de CI (auditoria de
dependências + cabeçalhos de segurança), registrados em
`docs/ROADMAP.md` → "Pendências / Ideias".

## 9. Limitações declaradas

1. **Frontend sem tela de login**: a autenticação é backend-only nesta onda; a
   SPA da Onda 7 opera em modo local. A integração de UI de login é uma
   pendência explícita.
2. **Rate limiter por processo**: sem estado compartilhado entre workers.
3. **`Transformations` como JSON**: as transformações por revisão são
   serializadas em `revisions.transformations_json`, sem tabela relacional
   dedicada (decisão de escopo, rastreabilidade por `rule_id` preservada).
4. **Sem tabelas `author_profiles`/`validation_reports`**: os perfis autorais
   são efêmeros (construídos por requisição) e os relatórios de validação são
   devolvidos na resposta, sem persistência dedicada.
