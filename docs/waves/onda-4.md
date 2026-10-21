# Onda 4 — Sistema de Templates ABNT

- **Data**: 2026-10-21
- **Escopo**: motor de estruturação e formatação acadêmica determinística,
  com templates versionados, herança e perfis institucionais.
- **Status**: concluída.

---

## 1. Escopo executado

| # | Entregável do ROADMAP | Onde | Estado |
|---|---|---|---|
| 1 | 8 templates ABNT | `templates/abnt/{general,articles,tcc,monographs,dissertations,theses,research_projects,reports}/` | ✅ |
| 2 | Perfis institucionais (UFMS/UFGD) + schema de upload | `templates/institutions/{ufms,ufgd}/` | ✅ |
| 3 | `structure.py` | `app/services/academic/structure.py` | ✅ |
| 4 | `metadata.py` | `app/services/academic/metadata.py` | ✅ |
| 5 | `sections.py` | `app/services/academic/sections.py` | ✅ |
| 6 | `numbering.py` (NBR 6024) | `app/services/academic/numbering.py` | ✅ |
| 7 | `pagination.py` | `app/services/academic/pagination.py` | ✅ |
| 8 | `styles.py` | `app/services/academic/styles.py` | ✅ |
| 9 | `api/v1/templates.py` | `app/api/v1/templates.py` | ✅ |

Módulos adicionais: `template_model.py` (modelos) e `templates.py` (loader e
resolvedor com herança e conflitos).

## 2. Funcionalidades concluídas

- **8 tipos de template** versionados e com fontes declaradas; cada um
  herda a formatação do `abnt.general` via `extends`.
- **Resolução por precedência** (`ADR-0007`): `instituição > template > norma`,
  com `TemplateResolved` e conflitos **registrados**, nunca ocultados.
- **Margens NBR 14724:2024 parametrizadas** no YAML (anverso 3/3/2/2 cm;
  verso 2/3/3/2 cm) — o código apenas as lê, nunca as hard-coda.
- **Perfis institucionais** UFMS (sobrescreve a fonte para Arial, com manual
  desatualizado 14724:2011 sinalizado) e UFGD (desativa espelhamento).
- **Estrutura determinística** (`structure.py`): detecção de títulos por
  Markdown, numeração progressiva e títulos sem indicativo — sem LLM.
- **Numeração progressiva** (`numbering.py`, NBR 6024), **paginação**
  (`pagination.py`, anverso/verso e posição do número), **estilos**
  (`styles.py`), **classificação** pré/textual/pós (`sections.py`) e
  **metadados** (`metadata.py`).
- **API** `/api/v1/templates`: listagem, detalhe e `resolve` com perfil
  institucional e registro de conflitos.
- **Ficha catalográfica reservada** (nunca fictícia) e **sumário como campo
  TOC real** do Word (marcado, não texto digitado).

## 3. Arquivos criados ou modificados

- **Criados (backend)**: `app/services/academic/{__init__,template_model,templates,structure,numbering,pagination,styles,sections,metadata}.py`,
  `app/schemas/templates.py`, `app/api/v1/templates.py`,
  `tests/conftest.py`,
  `tests/unit/{test_academic_templates,test_academic_numbering,test_academic_structure,test_academic_pagination,test_academic_styles,test_academic_sections,test_academic_metadata}.py`,
  `tests/integration/test_templates_api.py`.
- **Criados (templates)**: `templates/abnt/{articles,tcc,monographs,dissertations,theses,research_projects,reports}/*.yaml`,
  `templates/institutions/{ufms/ufms.yaml,ufgd/ufgd.yaml}`.
- **Modificados**: `app/api/router.py` (rota), `app/main.py` (estado
  `template_registry`), `templates/schemas/template.schema.json` (requisitos
  mínimos para `kind: instituicao`), `backend/pyproject.toml` (mypy ignore
  `yaml.*`), `templates/README.md`.
- **Documentação**: `docs/ARCHITECTURE.md` (§7.4), `docs/ROADMAP.md` (estado),
  `README.md` (estado), `docs/waves/onda-4.md`.

## 4. Testes realizados

| Suíte | Testes |
|---|---|
| Templates (loader/resolver, unitário) | 12 |
| Numeração (unitário) | 7 |
| Estrutura (unitário) | 5 |
| Paginação (unitário) | 5 |
| Estilos (unitário) | 5 |
| Seções (unitário) | 5 |
| Metadados (unitário) | 4 |
| API (integração) | 6 |
| Subtotal Onda 4 | **49** |
| Ondas 0–3 | 303 |
| **Total** | **352** |

Cobertura de `app/services/academic/`: **96%** (mínimo exigido: 80%).

## 5. Resultados obtidos (com saída real dos comandos)

```
$ ruff check .
All checks passed!

$ ruff format --check .
112 files already formatted

$ mypy .
Success: no issues found in 111 source files

$ pytest
352 passed in 9.26s

$ pytest --cov=app/services/academic --cov-report=term
TOTAL    374     16    96%
```

Verificação da API (TestClient):

```
GET  /api/v1/templates          → 10 templates (8 ABNT + 2 institucionais)
GET  /api/v1/templates/abnt.tcc → font "Times New Roman"
GET  /api/v1/templates/abnt.tcc/resolve?instituicao=inst.ufms.geral
     → font "Arial"; conflitos: typography.font (Arial) e
       fonte.ABNT NBR 14724 (14724:2011, desatualizada)
GET  /api/v1/templates/nao_existe → 404
```

## 6. Pendências

| Pendência | Onda | Observação |
|---|---|---|
| `jsonschema` como dependência de validação | 5/6 | validação feita pelo carregador; schema existe |
| Ficha catalográfica de fato vazia no DOCX | 6 | hoje é o elemento `catalog_record` com nota de reserva |
| Campo TOC real gerado no DOCX | 6 | `TOC_IS_FIELD` marcado; exportação é da Onda 6 |
| `PERSON`/`INSTITUTION` em citações | 5 | NBR 6023/10520 |
| Upload de perfil institucional via UI | 7 | schema pronto; UI é da Onda 7 |

## 7. Riscos conhecidos

- **Conformidade presumida**: não ocorre — cada regra declara fonte e
  confiança (`ADR-0015`); o relatório é por regra.
- **Manual institucional desatualizado (UFMS 14724:2011)**: sinalizado como
  conflito `fonte.*` com severidade `warning`, nunca aplicado em silêncio.
- **Reprodução de norma protegida**: não ocorre — o repositório guarda
  parâmetros e referências, nunca texto integral de norma.
- **Detecção de estrutura é heurística**: títulos sem indicativo usam uma
  lista fechada de nomes conhecidos; refinamento é da Onda 5.

## 8. Próxima onda recomendada

**Onda 5 — Citações, Referências e Validador ABNT**: formatação de citações
(NBR 10520:2023), referências (NBR 6023:2025) e relatórios auditáveis.
**Não iniciar sem autorização expressa.**

## 9. Limitações declaradas

1. **A geração efetiva do documento (DOCX/PDF) é da Onda 6.** Esta onda
   entrega o **motor de estruturação e formatação** e os templates; o campo
   TOC real e a ficha catalográfica vazia serão materializados no exportador.
2. **`jsonschema` não foi adicionado** como dependência; a validação é feita
   pelo carregador (`TemplateRegistry`), e o schema permanece disponível para
   validação manual.
3. **Perfis institucionais são parciais**: declaramos apenas o que as fontes
   públicas permitem confirmar; nenhuma conformidade é presumida.
4. **A detecção de títulos sem indicativo** cobre os nomes mais comuns do
   Esquema 1 da NBR 14724:2024, não todas as variações possíveis.
