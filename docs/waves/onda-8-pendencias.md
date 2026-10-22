# Onda 8 — Pendências de segurança autorizadas

> Escopo autorizado pelo responsável em 2026-10-22: revogação persistida, rate
> limit via Redis, cofre de chaves de LLM, execução do e2e e teste dos
> cabeçalhos do Nginx. **Sem commit.** Decisões em `ADR-0018`.

## 1. Escopo executado

Fechamento de quatro pendências do `docs/ROADMAP.md` §3 / `ADR-0017`.

## 2. Funcionalidades concluídas

| Pendência | Entrega |
|---|---|
| Revogação persistida | `RevocationStore` (contrato em `core`), `InMemoryRevocationStore`, `SqlRevocationStore` (repositório), modelos `RevokedToken`/`RevokedSubject`, migração `0003_token_revocations`, config `REVOCATION_BACKEND` (padrão `database`) |
| Rate limit via Redis | `RedisSlidingWindowLimiter` reescrito com script Lua atômico (`EVAL`) e relógio `TIME` do Redis; `connect_redis`; `REDIS_URL`; extra opcional `redis`; inicialização falha sem URL/extra |
| Cofre de chaves de LLM | `OPENAI_/ANTHROPIC_/GEMINI_/OPENAI_COMPATIBLE_API_KEY_ENV_NAME`, lidos a cada resolução; valor direto tem precedência; nomes reservados e inválidos rejeitados |
| e2e + Nginx | Playwright executado; `tests/unit/nginxHeaders.test.ts` (estático); verificação manual em contêiner `nginx:alpine` |

## 3. Arquivos criados ou modificados

**Backend**
- Novos: `app/models/revocation.py`, `app/repositories/revocations.py`,
  `alembic/versions/0003_token_revocations.py`, `tests/unit/test_revocation_store.py`
- Modificados: `app/core/security.py`, `app/core/ratelimit.py`, `app/core/config.py`,
  `app/main.py`, `app/models/__init__.py`, `app/services/providers/credentials.py`,
  `pyproject.toml` (extra `redis`; dev `fakeredis[lua]`), `uv.lock`,
  `tests/conftest.py`, `tests/unit/test_security.py`, `tests/unit/test_ratelimit.py`,
  `tests/unit/test_config.py`, `tests/unit/test_provider_credentials.py`,
  `tests/integration/test_alembic_migrations.py`

**Frontend**
- Novo: `tests/unit/nginxHeaders.test.ts`

**Documentação**
- Novos: `docs/decisions/ADR-0018-revocation-redis-key-indirection.md`, este relatório
- Modificados: `docs/DECISIONS.md`, `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md`,
  `docs/ROADMAP.md`, `docs/architecture/SECURITY_REVIEW.md`, `docs/HANDOFF.md`,
  `.env.example`

## 4. Testes realizados

- Revogação: sobrevive a um novo `TokenService` (simula outro processo/reinício);
  `revoke_subject` de um processo invalida token emitido por outro; poda.
  Todos os testes de autenticação da API agora usam `SqlRevocationStore`.
- Redis: script Lua real via `fakeredis[lua]`; limite compartilhado entre dois
  clientes; 40 chamadas concorrentes em 4 clientes respeitam o limite 5;
  `connect_redis("")` falha; `create_app` sem `REDIS_URL` falha; com Redis
  monta `RedisSlidingWindowLimiter` em login e humanização.
- Cofre: leitura via variável indicada, rotação sem reinício, precedência do
  valor direto, variável ausente → indisponível, rejeição de `SECRET_KEY`,
  `encryption_key`, `DATABASE_URL` e nomes inválidos.
- Migração: `upgrade → downgrade → upgrade` cria as tabelas de revogação.
- Nginx: teste estático validado por mutação (remover `X-Frame-Options` de
  `/assets/` faz o teste falhar).

## 5. Resultados obtidos

```
backend$ ruff format --check .   → 188 files already formatted
backend$ ruff check .            → All checks passed!
backend$ mypy                    → Success: no issues found in 117 source files
backend$ pytest                  → 534 passed in 21.22s   (cobertura TOTAL 96%)
frontend$ npm run lint / typecheck → sem erros
frontend$ npx vitest run         → 22 testes passados
frontend$ npx playwright test    → 1 passed (fluxo completo sem segredos no navegador)

nginx:alpine (contêiner local, removido após o teste) — curl -I:
  /, /editor, /assets/index-*.js → X-Content-Type-Options, X-Frame-Options,
  Referrer-Policy e Content-Security-Policy presentes em todos
```

## 6. Pendências

- `*_API_KEY_FILE` (segredo em arquivo), rota administrativa de
  `revoke_subject`, serviço `redis` opcional no `docker-compose.yml` e
  `Cache-Control` duplicado em `/assets/` — registrados no `ROADMAP.md` §3.
- Nada foi commitado (pedido explícito).

## 7. Riscos conhecidos

- **`alembic upgrade head` obrigatório**: sem a migração `0003`, todo login,
  logout e requisição autenticada falha (tabelas ausentes) com
  `REVOCATION_BACKEND=database`, que é o padrão.
- Cada requisição autenticada faz até duas consultas por chave primária ao banco.
- O teste do Nginx é estático; a verificação contra servidor real foi manual.

## 8. Próxima onda recomendada

Nenhuma iniciada. Aguardando autorização do responsável.

## 9. Limitações declaradas

- Concorrência do Redis foi testada contra `fakeredis` (Lua real, servidor
  simulado), não contra um Redis real.
- `memory` (rate limit e revogação) segue por processo, para instalação de nó único.
