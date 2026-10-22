# Revisão técnica — ajustes pendentes (pós-Onda 8)

> **Para quem:** agente responsável por aplicar as correções.
> **Data da revisão:** 2026-10-22
> **Base:** commit `71f1147` + alterações **não commitadas** do working tree
> (27 arquivos modificados + 5 novos; ver `git status`). O `docs/HANDOFF.md`
> descreve essas alterações como concluídas — esta revisão mostra que parte
> delas está incompleta ou incorreta.
>
> Leia `AGENTS.md` antes de começar. **Não commitar sem pedido explícito.**
>
> **Status (2026-10-22): A1–A16 aplicados** (sem commit). Resultado e
> verificações em `docs/waves/onda-8-correcoes.md`; decisões em `ADR-0017`.
> Para A3 foi escolhida a opção 1 (remover `redis` da configuração).

---

## 0. Estado verificado

| Verificação | Resultado |
|---|---|
| `ruff check .` | ✅ sem erros |
| `ruff format --check .` | ✅ 180 arquivos formatados |
| `mypy` (strict) | ✅ 115 arquivos sem erros |
| `pytest` | ✅ todos passam — cobertura total 95% |
| frontend `lint` / `typecheck` / `vitest` / `build` | ✅ (17 testes) |

A suíte verde **não** detecta os problemas abaixo — cada item exige um teste
novo que falhe antes da correção.

---

## 1. Ajustes — ordem de prioridade

### P0 — Bugs que quebram em runtime

#### A1. `PREVIOUS_SECRET_KEYS` / `PREVIOUS_ENCRYPTION_KEYS` em CSV derrubam a aplicação
- **Onde:** `backend/app/core/config.py:86`, `:95`; `.env.example` diz "CSV/JSON".
- **Reprodução:** `PREVIOUS_SECRET_KEYS="a,b" python -c "from app.core.config import Settings; Settings()"`
  → `SettingsError: error parsing value for field "previous_secret_keys"`.
  O pydantic-settings só aceita JSON para `list[str]`.
- **Correção:** anotar os campos com `Annotated[list[str], NoDecode]` e um
  `field_validator(mode="before")` que aceite JSON **ou** CSV (strip + descartar vazios).
  Valor vazio (`PREVIOUS_SECRET_KEYS=`) deve resultar em `[]`.
- **Teste:** unitário em `tests/unit/test_config.py` (ou equivalente) com CSV, JSON e vazio.

#### A2. Download de exportação não envia o token
- **Onde:** `frontend/src/services/api.ts:175` — `fetch` direto, sem `Authorization`.
- **Efeito:** com `AUTH_ENABLED=true` todo download retorna 401.
- **Correção:** extrair um helper `cabecalhosAutenticacao()` reutilizado por `requisicao`
  e pelo download (não forçar `Content-Type: application/json` no GET binário).
- **Teste:** vitest que mocka `fetch` e verifica o header `Authorization` no download
  após `definirToken('x')`.

#### A3. `RATE_LIMIT_BACKEND=redis` cai silenciosamente para memória
- **Onde:** `backend/app/main.py` (`build_rate_limiter(...)` sem `redis_client`);
  `backend/app/core/ratelimit.py` (`build_rate_limiter` faz fallback sem aviso).
- **Efeito:** a configuração promete limite compartilhado entre nós e entrega limite
  por processo. `HANDOFF.md` e `SECURITY_REVIEW.md` marcam como ✅.
- **Correção (escolher uma, registrar a decisão em `docs/DECISIONS.md`):**
  1. Remover `"redis"` do `Literal` em `Settings` até existir cliente/dep. `redis`
     (mantendo a classe `RedisSlidingWindowLimiter` como contrato testado); **ou**
  2. Adicionar `REDIS_URL` + dependência `redis` (licença MIT — justificar no relatório,
     regra §7) e construir o cliente no `create_app`.
  Em qualquer caso, `build_rate_limiter` deve **lançar `ValueError`** quando o backend
  pedido não puder ser construído, em vez de cair para memória.
- **Observação adicional:** `RedisSlidingWindowLimiter.allow` faz
  `ZREMRANGEBYSCORE → ZCARD → ZADD` sem atomicidade entre nós (o `threading.Lock` é por
  processo). Se a opção 2 for escolhida, usar `MULTI/EXEC` ou script Lua.
- **Teste:** `build_rate_limiter(backend="redis", redis_client=None)` levanta erro.

#### A4. `document_id` aceita 120 caracteres, mas a coluna tem 32
- **Onde:** `backend/app/schemas/exports.py:24,43` (`max_length=120`) vs
  `backend/app/models/export.py` (`document_id: String(32)`).
- **Efeito:** em PostgreSQL, `POST /exports` com `document_id` > 32 chars gera
  `DataError` → 500 (`_persistir_registros` só captura `OperationalError`).
  No SQLite passa despercebido.
- **Correção:** alinhar tamanhos. Preferível: nova migração Alembic
  (`0002_...`) ampliando `exports.document_id` para `String(120)` e ajustando o modelo.
  **Não** usar `create_all`.
- **Teste:** integração com `document_id` de 100 caracteres; teste de migração
  `alembic upgrade head` em SQLite.

### P1 — Segurança

#### A5. Rate limiter atrás do Nginx usa o IP falsificável
- **Onde:** `backend/app/core/ratelimit.py` (`client_ip`), `frontend/nginx.conf`
  (`proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for`).
- **Problema:** `$proxy_add_x_forwarded_for` **anexa** o IP real ao XFF enviado pelo
  cliente; `client_ip` pega o **primeiro** item, que é controlado pelo atacante.
  Com `BEHIND_PROXY=true`, basta variar `X-Forwarded-For` para escapar do limite de login.
- **Correção:** usar o **último** item do XFF (o adicionado pelo proxy confiável), ou
  parametrizar `TRUSTED_PROXY_HOPS` (padrão 1) e pegar o item `-hops`. Atualizar a
  docstring e `docs/DEPLOYMENT.md`.
- **Teste:** `X-Forwarded-For: 1.2.3.4, 10.0.0.9` com `trust_proxy=True` → `10.0.0.9`.

#### A6. Cabeçalhos de segurança somem em `/assets/`
- **Onde:** `frontend/nginx.conf` — o bloco `location /assets/` declara `add_header`,
  o que, no Nginx, **anula** todos os `add_header` herdados do `server`.
- **Correção:** repetir os cabeçalhos no bloco (ou usar um `include` de snippet comum).
  Mesma verificação no exemplo de `docs/DEPLOYMENT.md`.
- **Teste:** manual/documentado (`curl -I http://localhost:5173/assets/<arquivo>.js`).

#### A7. Logout do frontend não revoga o token
- **Onde:** `frontend/src/context/AuthContext.tsx` (`sair` só limpa memória).
- **Correção:** `api.sair()` → `POST /auth/logout` (ignorar falha de rede), depois
  `definirToken(null)`. Adicionar tratamento de **401** em `requisicao` que limpa a sessão
  (token expirado deixa a UI "logada").
- **Teste:** vitest verificando chamada a `/auth/logout` e limpeza em 401.

#### A8. Revogação de tokens: memória ilimitada e não compartilhada
- **Onde:** `backend/app/core/security.py` (`_revoked_jtis`, `_revoked_subjects_before`).
- **Problemas:** (a) o `set` cresce indefinidamente — guardar `jti → exp` e podar
  expirados a cada `revoke_token`/`verify`; (b) revogação perdida no restart e não
  vista por outros workers. (b) pode ficar como **limitação declarada** (já consta em
  `SECURITY_REVIEW.md`) — mas `HANDOFF.md`/relatório precisam dizer isso explicitamente.
  `revoke_subject` não tem nenhum chamador na API — documentar como uso administrativo.
- **Teste:** token expirado revogado é removido da estrutura após poda.

#### A9. Hash de senha bloqueia o event loop
- **Onde:** `backend/app/api/v1/auth.py` — `registrar`/`login` são `async def` e chamam
  `hash_password`/`verify_password` (Argon2id 19 MiB / PBKDF2 600k) de forma síncrona.
- **Correção:** `await asyncio.to_thread(verify_password, ...)` e idem para `hash_password`
  (inclusive no rehash). Alternativa: transformar as rotas em `def` síncronas.
- **Teste:** os existentes devem continuar passando.

#### A10. Pino mínimo de `cryptography` incompatível com Argon2id
- **Onde:** `backend/pyproject.toml` — `cryptography>=43.0`; `Argon2id` só existe a partir
  da **44.0**. Instalação com 43.x quebra no import de `app.core.security`.
- **Correção:** `cryptography>=44.0` e regenerar `uv.lock` (não editar à mão).

### P2 — Robustez e correção funcional

#### A11. Loop de retenção morre na primeira exceção
- **Onde:** `backend/app/main.py` (`_loop_retencao`).
- **Correção:** envolver cada iteração em `try/except Exception` com
  `logger.exception("retencao.varredura_falhou")` e seguir o loop.
- **Teste:** `run_retention_sweep` mockado lançando erro uma vez; o loop executa a 2ª iteração.

#### A12. Retenção remove metadados de exportação mas deixa o arquivo em disco
- **Onde:** `ExportRepository.prune_expired` e `run_retention_sweep`
  (`session.delete(Export)`); `POST /documents/retention` também.
- **Efeito:** arquivos em `export_dir` cujo registro ORM sumiu ficam órfãos (o
  `export_store.prune_expired` só conhece registros em memória).
- **Correção:** ao apagar `Export`, apagar também `export_dir / filename`
  (com a mesma checagem `is_relative_to` usada no download).
- **Teste:** arquivo é removido junto com a linha.

#### A13. `PruneResponse.removidos` mistura documentos e exportações
- **Onde:** `backend/app/api/v1/documents.py` (`aplicar_retencao`).
- **Correção:** separar os contadores no schema (`documentos`, `exportacoes`) mantendo
  `removidos` como total, para não quebrar o frontend. Atualizar tipos TS.

#### A14. Limiter SQLite: conexões não fechadas e tabela sem poda global
- **Onde:** `backend/app/core/ratelimit.py` (`SqliteSlidingWindowLimiter`).
- **Problemas:** `with sqlite3.connect(...) as conn` **não fecha** a conexão (o context
  manager do sqlite3 só faz commit/rollback); `PRAGMA journal_mode=WAL` é reexecutado em
  cada requisição; linhas de chaves que não voltam nunca são apagadas.
- **Correção:** `contextlib.closing(...)`; WAL só em `_init_schema`; poda global
  ocasional (`DELETE ... WHERE ts <= ?` sem filtro de chave, p. ex. a cada N chamadas).
- **Teste:** após janela expirar, chamadas de outra chave podam as linhas antigas.

#### A15. Inspetor nativo de PDF declara margens sem verificá-las
- **Onde:** `backend/app/services/document_export/pdf_builder.py`
  (`_inspecionar_pdf_nativo`: `margins_respected=size_matches`,
  `pdf_non_empty_pages=page_count`).
- **Problema:** viola AGENTS.md §5 ("não declarar conformidade sem validação"). Além disso,
  a regex sobre bytes brutos não enxerga objetos dentro de *object streams* (PDF ≥ 1.5
  comprimido) e tende a contar 0 páginas nesses arquivos (não verificado com saída real
  do LibreOffice — confirmar).
- **Correção:** `margins_respected=False` + entrada em `limitations`
  ("margens não verificadas pelo inspetor nativo"); se `page_count == 0` com `%PDF-`
  válido, registrar limitação "estrutura comprimida não inspecionável" em vez de
  `pagination_valid=False` silencioso.
- **Teste:** atualizar `test_compare_docx_and_pdf_fallback_nativo_sem_pymupdf`.

#### A16. Pequenos
- `SecretCipher.decrypt` usa `assert` em código de produção (removido com `-O`) — trocar
  por `raise InvalidTag()` explícito. (`backend/app/services/providers/credentials.py`)
- `needs_rehash` só olha o prefixo; considerar também parâmetros Argon2 diferentes dos
  atuais (`m`, `t`, `p`) para permitir endurecimento futuro.
- `Login.tsx`: `autoComplete="off"` na senha → `current-password` / `new-password`
  conforme o modo.
- `frontend/vite.config.ts:23` `sourcemap: true` publica sourcemaps no Nginx de produção —
  usar `'hidden'` ou condicionar ao modo.
- `ExportRepository` não tem teste unitário próprio (só coberto indiretamente).

---

## 2. Conformidade com o processo (`AGENTS.md`)

Estas alterações não pertencem a nenhuma onda nomeada nem têm relatório. Antes de
entregar:

1. **Decisões** (regra §3.13): registrar em `docs/DECISIONS.md` + `docs/decisions/`:
   Argon2id + rehash; rotação de chaves; backends de rate limit (inclui decisão de A3);
   inspetor nativo de PDF; retenção agendada.
2. **ROADMAP** (§3.14): atualizar `docs/ROADMAP.md` (seção 3 "Pendências") com o que foi
   feito e o que ficou como limitação (revogação por processo, Redis).
3. **Relatório:** gerar relatório no formato de `docs/ROADMAP.md` (ex.:
   `docs/waves/onda-8.1.md` ou o nome que o responsável definir).
4. **Corrigir `docs/HANDOFF.md` e `docs/architecture/SECURITY_REVIEW.md`**: hoje marcam
   como ✅ itens que não estão completos (Redis, revogação, logout no frontend).
5. **ARCHITECTURE.md / DEPLOYMENT.md:** documentar `RATE_LIMIT_BACKEND`,
   `RETENTION_SWEEP_INTERVAL_SECONDS`, `PREVIOUS_*_KEYS` e `ratelimit.db` em
   `storage_dir`.

> Fora de escopo: qualquer item novo além dos listados vai para
> `docs/ROADMAP.md` → "Pendências / Ideias", não para o código.

---

## 3. Definição de pronto desta tarefa

- [x] A1–A15 resolvidos (ou, quando indicado, declarados como limitação documentada).
- [x] Cada correção tem teste que falharia sem ela.
- [x] `cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy && .venv/bin/python -m pytest`
- [x] `cd frontend && npm run lint && npm run typecheck && npx vitest run && npm run build`
- [x] `alembic upgrade head` limpo em banco SQLite novo (por causa de A4).
- [x] Documentação da seção 2 atualizada.
- [x] Nenhum commit sem autorização; ao commitar, só arquivos intencionais.
