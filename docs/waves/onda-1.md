# Onda 1 — Normalização Textual

- **Data**: 2026-10-21
- **Escopo**: motor determinístico de limpeza de texto, sem LLM, com API e
  interface mínima.
- **Status**: concluída.

---

## 1. Escopo executado

| # | Entregável do ROADMAP | Onde | Estado |
|---|---|---|---|
| 1 | `engine.py` — pipeline determinístico | `app/services/normalizer/engine.py` | ✅ |
| 2 | `rules/` — uma classe por transformação, `rule_id` estável | `app/services/normalizer/rules/` | ✅ |
| 3 | `protect.py` — segmentação protegidos/livres | `app/services/normalizer/protect.py` | ✅ |
| 4 | `profile.py` — `NormalizationProfile` | `app/services/normalizer/profile.py` | ✅ |
| 5 | `stats.py` — `NormalizationReport` | `app/services/normalizer/stats.py` | ✅ |
| 6 | `schemas/normalize.py` — request/response | `app/schemas/normalize.py` | ✅ |
| 7 | `api/v1/normalize.py` — `POST /api/v1/normalize` | `app/api/v1/normalize.py` | ✅ |
| 8 | Frontend mínimo em `pages/Normalizacao.tsx` | `frontend/src/pages/Normalizacao.tsx` | ✅ |
| 9 | Regras de preservação (28 `rule_id` + 1 linha) | `app/services/normalizer/rules/` | ✅ |
| 10 | Regressão documental (`tests/fixtures/`) | `backend/tests/fixtures/` | ✅ |

## 2. Funcionalidades concluídas

- **Motor determinístico** (`NormalizationEngine`): 29 regras em ordem fixa
  (`PIPELINE_ORDER`), sem LLM e sem rede. A mesma entrada e o mesmo perfil
  produzem sempre a mesma saída.
- **Proteção de conteúdo** (`protect.py`): o texto é segmentado em trechos
  protegidos e livres; cada regra declara `protected_kinds` e é aplicada
  apenas fora dos trechos que não pode alterar. O catálogo de entidades
  protegidas usa o IR (`app/ir/protection.py`) e é recalculado ao fim —
  qualquer **perda ou alteração** vira aviso no relatório.
- **29 regras**, cobrindo invisíveis, Unicode (NFKC/NFC), espaços, pontuação,
  Markdown, símbolos (emoji, pseudo-gráficos, traços, aspas, reticências,
  marcadores), controle/ANSI e entidades HTML.
- **Perfis** (`padrao`, `conservador`, `agressivo`) e **opções** da interface
  (NFKC, invisíveis, emojis, Markdown, espaços) que ligam/desligam grupos de
  regras.
- **API**: `POST /api/v1/normalize` (texto + relatório por regra + entidades
  protegidas + avisos) e `GET /api/v1/normalize/perfis`.
- **Frontend** (`/normalizacao`): editor com contador, 5 opções, painel lado
  a lado com destaque das alterações (diff por palavras), estatísticas por
  regra, avisos, entidades protegidas, botão de copiar e exportação TXT/Markdown.

## 3. Arquivos criados ou modificados

- **Criados (backend)**: `app/services/normalizer/{engine,protect,profile,stats}.py`,
  `app/services/normalizer/rules/{__init__,invisibles,unicode_rules,whitespace,punctuation,markdown,symbols,html_entities}.py`,
  `app/schemas/normalize.py`, `app/api/v1/normalize.py`,
  `backend/tests/{unit/test_normalizer_rules.py,unit/test_normalizer_protect.py,unit/test_normalizer_engine.py,unit/test_normalizer_profile.py,integration/test_normalize_api.py,regression/test_regressao_documental.py}`,
  `backend/tests/fixtures/{artigo_cientifico.md,artigo_cientifico_esperado.txt}`.
- **Modificados (backend)**: `app/services/normalizer/rules/base.py`
  (`RuleGroup`, `protected_kinds`, `RegexRule`), `app/ir/protection.py`
  (`ProtectedKind.TABLE`), `app/api/router.py` (registro da rota),
  `app/services/normalizer/__init__.py` (exports).
- **Criados (frontend)**: `src/pages/Normalizacao.tsx`, `src/utils/diff.ts`.
- **Modificados (frontend)**: `src/App.tsx` (rota + acentos), `src/services/api.ts`
  (`normalize`, `normalizePerfis`), `src/types/index.ts` (tipos).
- **Documentação**: `docs/ARCHITECTURE.md` (mapa de regras), `docs/ROADMAP.md`
  (estado e critérios), `README.md` (estado do projeto), `docs/waves/onda-1.md`.

## 4. Testes realizados

| Suíte | Testes | Cobertura (`app/services/normalizer/`) |
|---|---|---|
| Regras (unitário, por regra) | 96 | — |
| Proteção (unitário) | 22 | 99% (`protect.py`) |
| Motor (unitário) | 22 | 97% (`engine.py`) |
| Perfis (unitário) | 8 | 98% (`profile.py`) |
| API (integração) | 7 | — |
| Regressão documental | 4 | — |
| Subtotal Onda 1 | **159** | **98%** |
| Onda 0 (IR, logging, smoke) | 29 | — |
| **Total** | **188** | **98%** (mínimo exigido: 80%) |

## 5. Resultados obtidos (com saída real dos comandos)

```
$ ruff check .
All checks passed!

$ ruff format --check .
56 files already formatted

$ mypy .
Success: no issues found in 55 source files

$ pytest
188 passed in 0.52s

$ pytest --cov=app/services/normalizer --cov-report=term
TOTAL                                              834     14    98%

$ npx tsc --noEmit
(sem saída — nenhum erro de tipo)

$ npx vite build
dist/index.html                   0.54 kB │ gzip:  0.34 kB
dist/assets/index-CRPVlEiZ.css    9.11 kB │ gzip:  2.54 kB
dist/assets/index-QvAIYoCp.js   176.73 kB │ gzip: 57.81 kB │ map: 737.33 kB
✓ built in 897ms
```

Verificação da API ao vivo (TestClient):

```
POST /api/v1/normalize  {"texto": "# Título\n\na   b com 10⁻⁶ m² e (Silva, 2020)"}
→ texto:            "Título\n\na b com 10⁻⁶ m² e (Silva, 2020)"
→ transformacoes:   [("norm.markdown.heading", 1), ("norm.whitespace.collapse", 1)]
→ protegidas:       [("formula", "10⁻⁶"), ("formula", "m²"), ("citation", "(Silva, 2020)")]
→ avisos:           ["atencao: a regra norm.unicode.nfkc foi mantida desligada ..."]
```

## 6. Pendências

| Pendência | Onda | Observação |
|---|---|---|
| Detecção de `REFERENCE` depende de cabeçalho "Referências" | 4 | a estruturação completa é da Onda 4 |
| `PERSON`/`INSTITUTION`/`SPECIMEN` não extraídos | 3 | exigem NER/semântica |
| `TABLE` protegido como bloco de linhas com `\|`/caixa | 4 | o `TableData` estruturado é da Onda 4 |
| Emoji: lista de exceção é heurística, não exaustiva | 7 | revisar com usuários |
| `norm.quotes.ascii` ligada por padrão, preserva só citação literal | — | decisão revisável |
| Frontend sem testes (Vitest/Testing Library) | 7 | dependências declaradas, sem suite |

## 7. Riscos conhecidos

- **R-01** (NFKC destrói `10⁻⁶`) — mitigado: `norm.unicode.nfkc` desligada
  por padrão e restrita a trechos não protegidos; teste de regressão cobre
  `10⁻⁶`, `x²`, `Na⁺`, `CO₂`, `m·a`.
- **R-05** (U+2212 → hífen) — mitigado: `norm.dash.normalize` não alcança
  U+2212 e o protege como fórmula.
- **R-10** (NFKC × limpeza de Markdown) — mitigado: ordem fixa NFKC antes de
  Markdown; idempotência testada.
- **Regressões §6.3–6.7 do repositório de referência** (subscritos `_i_`,
  setas `→`, `©®™`, tabelas) — cobertas por teste de regressão documental.
- **Perda de conteúdo protegido** — detectada e reportada como aviso
  (`houve_perda`); nenhuma perda no fixture atual.

## 8. Próxima onda recomendada

**Onda 2 — Integração Multi-LLM**: `registry.py`, adaptadores (OpenAI,
Anthropic, Gemini, Ollama, OpenAI-compat), `credentials.py` (resolução de
chave sem nunca expô-la), `resilience.py` (timeout/retry/rate limit) e
`usage.py` (custo). Exige `app/services/providers/base.py` (já existe como
contrato). **Não iniciar sem autorização expressa.**

## 9. Limitações declaradas

1. **A normalização opera sobre texto plano**, não sobre o IR estruturado.
   A estruturação do documento (blocos, tabelas como `TableData`) é da Onda 4.
2. **A detecção de entidades protegidas é lexical**, não semântica. Termos
   definidos, pessoas e instituições não são identificados nesta onda.
3. **A lista de exceção de emoji é heurística.** Pode haver pictogramas
   técnicos não cobertos; a remoção é conservadora e preserva `©`, `®`, `™`.
4. **`norm.quotes.ascii` converte aspas curvas fora de citações literais.**
   A detecção de citação literal é lexical (pares de aspas curvas) e será
   refinada na Onda 3.
5. **O frontend não tem suíte própria de testes** — a cobertura exigida pelo
   ROADMAP incide sobre o backend. A suíte Vitest/Testing Library é da Onda 7.
6. **Não há persistência nem histórico** nesta onda; a API é stateless.
7. **A normalização não gera relatório de conformidade ABNT** — isso é
   responsabilidade das ondas 4 e 5.
8. **Nenhuma chamada a LLM pago foi realizada** durante a onda.
