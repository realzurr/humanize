# Onda 2 — Integração Multi-LLM

- **Data**: 2026-10-21
- **Escopo**: camada de provedores de linguagem por uma interface comum, com
  resiliência, resolução de credenciais e estimativa de custo.
- **Status**: concluída.

---

## 1. Escopo executado

| # | Entregável do ROADMAP | Onde | Estado |
|---|---|---|---|
| 1 | `base.py` — contrato (já existia) | `app/services/providers/base.py` | ✅ (inalterado) |
| 2 | `registry.py` — resolução por id | `app/services/providers/registry.py` | ✅ |
| 3 | 5 adaptadores | `openai_provider.py`, `anthropic_provider.py`, `gemini_provider.py`, `ollama_provider.py`, `openai_compat.py` | ✅ |
| 4 | `credentials.py` — resolução (env/sessão cifrada) | `app/services/providers/credentials.py` | ✅ |
| 5 | `resilience.py` — timeout/retry/Retry-After | `app/services/providers/resilience.py` | ✅ |
| 6 | `usage.py` — tokens e custo | `app/services/providers/usage.py` | ✅ |
| 7 | `api/v1/providers.py` — GET/POST/DELETE | `app/api/v1/providers.py` | ✅ |

Módulos de apoio adicionados: `transport.py` (base HTTP compartilhada) e
`catalog.py` (tabela estática de modelos e preços aproximados).

## 2. Funcionalidades concluídas

- **Contrato neutro** (`LLMProvider`, `LLMRequest`, `LLMResponse`,
  `ChatMessage`, `TokenUsage`, `ProviderError`) — inalterado desde a Onda 0.
- **5 adaptadores HTTP** via `httpx` (sem SDKs, ver adendo ao `ADR-0004`):
  OpenAI, Anthropic (`max_tokens` obrigatório, prompt de sistema separado),
  Gemini (`systemInstruction` + `generationConfig`, chave na query), Ollama
  (sem chave) e OpenAI-compatível (endpoint e modelos configuráveis).
- **Resiliência** (`resilience.py`): timeout (`asyncio.timeout`), retry com
  backoff exponencial + jitter, respeito a `Retry-After` (segundos ou data
  HTTP) e mapeamento de erros HTTP para `ProviderError` (AUTH, RATE_LIMIT,
  TIMEOUT, NETWORK, QUOTA, MODEL_NOT_FOUND, CONTENT_FILTER, SERVER_ERROR,
  INVALID_RESPONSE, CANCELLED, UNKNOWN).
- **Credenciais** (`credentials.py`): cifra AES-GCM (`cryptography`), resolução
  com precedência env > sessão, e indicador público `configured`/`last4` — a
  chave nunca aparece em log, exceção ou resposta.
- **Estimativa** (`usage.py`): tokens por heurística (chars/4) com a contagem
  real do provedor tendo precedência; custo em USD a partir da tabela local.
- **API** (`/api/v1/providers`): listar provedores, listar modelos, armazenar
  e remover credencial (devolve só `configured`/`last4`); erro 404 para
  provedor desconhecido; validação de entrada com `extra="forbid"`.
- **Cancelamento** por `request_id` no transporte HTTP.

## 3. Arquivos criados ou modificados

- **Criados (backend)**: `app/services/providers/{resilience,usage,credentials,catalog,transport,registry,openai_provider,anthropic_provider,gemini_provider,ollama_provider,openai_compat}.py`,
  `app/schemas/providers.py`, `app/api/v1/providers.py`,
  `tests/unit/{test_provider_resilience,test_provider_credentials,test_provider_usage,test_provider_adapters,test_provider_registry}.py`,
  `tests/integration/test_providers_api.py`.
- **Modificados (backend)**: `app/services/providers/__init__.py` (exports),
  `app/api/router.py` (rota), `app/main.py` (estado `provider_registry` e
  `provider_resolver`).
- **Documentação**: `docs/decisions/ADR-0004-llm-provider-abstraction.md`
  (adendo transporte HTTP), `docs/ARCHITECTURE.md` (§5.1), `docs/ROADMAP.md`
  (estado e critérios), `README.md` (estado), `docs/waves/onda-2.md`.

## 4. Testes realizados

| Suíte | Testes |
|---|---|
| Resiliência (unitário) | 21 |
| Credenciais (unitário) | 10 |
| Uso/catálogo (unitário) | 8 |
| Adaptadores (unitário) | 14 |
| Registro (unitário) | 6 |
| API (integração) | 8 |
| Subtotal Onda 2 | **67** |
| Ondas 0–1 | 188 |
| **Total** | **255** |

Cobertura de `app/services/providers/`: **92%** (mínimo exigido: 80%).

## 5. Resultados obtidos (com saída real dos comandos)

```
$ ruff check .
All checks passed!

$ ruff format --check .
75 files already formatted

$ mypy .
Success: no issues found in 74 source files

$ pytest
255 passed in 7.38s

$ pytest --cov=app/services/providers --cov-report=term
TOTAL    668     52    92%
```

Verificação da API (TestClient):

```
GET  /api/v1/providers            → 5 provedores, com configured/last4
GET  /api/v1/providers/openai/models → [gpt-4.1, gpt-4.1-mini, gpt-4o, …]
POST /api/v1/providers/openai/credentials {"api_key": "sk-teste-abcdef123456"}
     → {"provedor": "openai", "configurado": true, "last4": "3456", "fonte": "session"}
DELETE /api/v1/providers/openai/credentials
     → {"provedor": "openai", "configurado": false, "last4": "", "fonte": ""}
GET  /api/v1/providers/nao_existe/models → 404 not_found
```

## 6. Pendências

| Pendência | Onda | Observação |
|---|---|---|
| Persistência cifrada em banco (multiusuário) | 8 | sessão é em memória; AES-GCM já implementado |
| Streaming real (SSE) nos adaptadores | 3/7 | o padrão `stream` delega a `generate` |
| Contagem precisa de tokens (`tiktoken`) | 3 | heurística chars/4 por enquanto |
| Tabela de preços é estática e aproximada | — | revisar periodicamente |
| `check_credentials` valida só a configuração | 3 | validação real da chave exige chamada (opt-in) |
| Página de configuração de LLM no frontend | 7 | fora do escopo desta onda |

## 7. Riscos conhecidos

- **Chave de API**: nunca em código, fixture, log, exceção ou resposta;
  verificada por teste dedicado (`test_erro_auth_nao_vaza_chave`).
- **Chamadas reais**: nenhuma feita durante a onda — os adaptadores são
  exercitados apenas com `httpx.MockTransport`.
- **Dependência de SDKs**: evitada (adendo ao `ADR-0004`); sem novas
  dependências — `httpx`, `tenacity` e `cryptography` já estavam no manifesto.
- **Prompt injection**: o documento importado é conteúdo, nunca instrução —
  tratado na Onda 3, quando os adaptadores serão usados para humanização.

## 8. Próxima onda recomendada

**Onda 3 — Humanização Semântica**: motor de revisão por LLM com perfis
autorais e intensidade, máscara de entidades protegidas antes da chamada,
validação semântica pós-revisão e `approval gate` (`ADR-0013`). **Não iniciar
sem autorização expressa.**

## 9. Limitações declaradas

1. **Os adaptadores usam HTTP direto, não SDKs oficiais** (decisão registrada
   no adendo do `ADR-0004`). Recursos específicos ficam em `metadata`.
2. **`list_models` devolve o catálogo estático**; a lista real de modelos
   locais do Ollama depende do que está instalado na máquina.
3. **`check_credentials` não valida a chave por chamada de rede** — apenas
   confirma a configuração; a validação real ocorre na primeira inferência.
4. **`stream` usa o padrão do contrato** (delega a `generate`); streaming real
   via SSE é da Onda 3/7.
5. **Preços e nomes de modelos são aproximados** e servem só para estimativa.
6. **Persistência é de sessão** (em memória); o armazenamento cifrado em banco
   é da Onda 8.
7. **Nenhuma chamada a LLM pago foi realizada** durante a onda.
