# Onda 3 — Humanização Semântica

- **Data**: 2026-10-21
- **Escopo**: motor de reescrita por LLM com perfis autorais, intensidade,
  análise de estilo e validação semântica (máscara/restauração/validação de
  dados protegidos).
- **Status**: concluída.

---

## 1. Escopo executado

| # | Entregável do ROADMAP | Onde | Estado |
|---|---|---|---|
| 1 | `humanizer/analysis.py` | `app/services/humanizer/analysis.py` | ✅ |
| 2 | `humanizer/profiles.py` (7 perfis) | `app/services/humanizer/profiles.py` | ✅ |
| 3 | `humanizer/intensity.py` | `app/services/humanizer/intensity.py` | ✅ |
| 4 | `humanizer/style_features.py` | `app/services/humanizer/style_features.py` | ✅ |
| 5 | `semantic_validator/` | `app/services/semantic_validator/` | ✅ |
| 6 | `api/v1/humanize.py` — `POST /api/v1/humanize` | `app/api/v1/humanize.py` | ✅ |

Módulo adicional: `humanizer/engine.py` (orquestração do ciclo completo).

## 2. Funcionalidades concluídas

- **7 perfis autorais** (`profiles.py`): acadêmico científico, acadêmico
  acessível, profissional, institucional, narrativo, conversacional e autoral
  personalizado — cada um com instrução de sistema distinta.
- **Intensidade** (`intensity.py`): 0/25/50/75/100 como parâmetro de
  orientação; 0 não altera nada e **não chama o provedor**.
- **Análise** (`analysis.py`): repetições, frases padronizadas, transições
  artificiais, coesão, vagueza, redundância, voz passiva e excesso de
  conectivos — determinístico, sem LLM.
- **Traços de estilo** (`style_features.py`): formalidade, vocabulário,
  comprimento médio de frase, construção argumentativa, conectivos,
  terminologia, organização de parágrafos e ritmo.
- **Validação semântica** (`semantic_validator/`): extração (reusa o extrator
  da normalização, acrescido de `TERM_DEFINED`), máscara (`⟦P0001⟧`),
  restauração e comparação de catálogos — detecta **perda**, **alteração** e
  **invenção** de números, com o portão de aprovação do `ADR-0013`.
- **Motor** (`engine.py`): máscara → chamada ao provedor → restauração →
  validação; o provedor **nunca** vê valores protegidos.
- **API** `POST /api/v1/humanize`: devolve texto revisado, análise, estilo,
  relatório de validação e consumo estimado.

## 3. Arquivos criados ou modificados

- **Criados (backend)**: `app/services/humanizer/{__init__,profiles,intensity,style_features,analysis,engine}.py`,
  `app/services/semantic_validator/{__init__,extractor,masker,validator}.py`,
  `app/schemas/humanize.py`, `app/api/v1/humanize.py`,
  `tests/unit/{test_humanizer_profiles,test_humanizer_intensity,test_humanizer_style_features,test_humanizer_analysis,test_humanizer_engine,test_semantic_validator,fakes}.py`,
  `tests/integration/test_humanize_api.py`.
- **Modificados (backend)**: `app/services/normalizer/protect.py`
  (`TERM_DEFINED` — sigla + definição), `app/api/router.py` (rota).
- **Documentação**: `docs/ARCHITECTURE.md` (§5.3), `docs/ROADMAP.md` (estado e
  critérios), `README.md` (estado), `docs/waves/onda-3.md`.

## 4. Testes realizados

| Suíte | Testes |
|---|---|
| Perfis (unitário) | 8 |
| Intensidade (unitário) | 4 |
| Traços de estilo (unitário) | 7 |
| Análise (unitário) | 7 |
| Validação/máscara (unitário) | 8 |
| Motor (unitário) | 8 |
| API (integração) | 6 |
| Subtotal Onda 3 | **48** |
| Ondas 0–2 | 255 |
| **Total** | **303** |

Cobertura de `app/services/humanizer/` + `app/services/semantic_validator/`:
**96%** (mínimo exigido: 80%).

## 5. Resultados obtidos (com saída real dos comandos)

```
$ ruff check .
All checks passed!

$ ruff format --check .
93 files already formatted

$ mypy .
Success: no issues found in 92 source files

$ pytest
303 passed in 6.91s

$ pytest --cov=app/services/humanizer --cov=app/services/semantic_validator
TOTAL    373     14    96%
```

Verificação do ciclo completo (fake provider ecoa o texto mascarado):

```
entrada:  "O valor medido foi de 45,5 % (p = 0,003) ... 10.1111/jss.12845 ..."
saída:    idêntica — nenhuma perda, nenhuma alteração, nenhuma invenção
mascarado: sem "45,5" nem "10.1111" (apenas ⟦P0001⟧…)
```

## 6. Pendências

| Pendência | Onda | Observação |
|---|---|---|
| Detecção de `PERSON`/`INSTITUTION`/`SPECIMEN` | 3+ | heurística NER ainda não implementada |
| Divergência de sentido (comparação semântica real) | 3+ | hoje a validação é lexical/fingerprint |
| Streaming (SSE) na humanização | 7 | adaptadores usam o padrão `generate` |
| Persistência de perfis autorais | 8 | perfil autoral vive em memória |
| Revisão humana ("aceitar mesmo assim") no frontend | 7 | `blocked` já é devolvido pela API |

## 7. Riscos conhecidos

- **Invenção de resultados**: mitigada — o modelo não vê números (máscara), e
  números novos na revisão geram achado `high` que **bloqueia** a aprovação.
- **Perda de dado protegido**: mitigada — entidade ausente gera achado com a
  severidade do nível da entidade; `CRITICAL` bloqueia.
- **Prompt injection**: o texto do autor é enviado como conteúdo com
  marcadores `⟦ ⟧`; a instrução de sistema proíbe seguir comandos do texto
  (reforçada na Onda 8 com delimitação explícita).
- **Nenhuma chamada paga foi feita**: todos os testes usam `FakeLLMProvider`.
- **Falsos negativos na extração** são possíveis (detecção heurística); o
  relatório de validação reflete apenas o que foi possível extrair.

## 8. Próxima onda recomendada

**Onda 4 — Sistema de Templates ABNT**: templates versionados (YAML/JSON),
gerador de estrutura acadêmica, precedência instituição > template > norma, e
validação do schema de template com `jsonschema`. **Não iniciar sem
autorização expressa.**

## 9. Limitações declaradas

1. **A validação é lexical e por fingerprint**, não comparação semântica de
   sentido. A detecção de divergência de sentido fina fica para ondas futuras.
2. **`PERSON`, `INSTITUTION` e `SPECIMEN` não são extraídos** nesta onda (a
   extração cobre as 14 categorias restantes + `TERM_DEFINED`).
3. **O perfil autoral é construído em memória** (sem persistência) e usa os
   textos fornecidos na própria requisição.
4. **A reescrita real depende do provedor**; sem um provedor configurado, o
   ciclo de teste usa *fake provider* (sem alteração de conteúdo).
5. **Nenhuma chamada a LLM pago foi realizada** durante a onda.
