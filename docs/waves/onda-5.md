# Onda 5 — Citações, Referências e Validador ABNT

- **Data**: 2026-10-21
- **Escopo**: módulo de integridade acadêmica (NBR 10520:2023 e NBR 6023:2025),
  importação de BibTeX e CSL-JSON, consulta opt-in de DOI com propostas de
  alteração e relatório auditável de validação.
- **Status**: concluída.

---

## 1. Escopo executado

| # | Entregável do ROADMAP | Onde | Estado |
|---|---|---|---|
| 1 | `references/models.py` | `app/services/references/models.py` | ✅ |
| 2 | `references/parser.py` | `app/services/references/parser.py` | ✅ |
| 3 | `references/citation_parser.py` | `app/services/references/citation_parser.py` | ✅ |
| 4 | `references/matcher.py` | `app/services/references/matcher.py` | ✅ |
| 5 | `references/nbr6023.py` | `app/services/references/nbr6023.py` | ✅ |
| 6 | `references/bibtex.py` e `references/csl_json.py` | `app/services/references/{bibtex,csl_json}.py` | ✅ |
| 7 | `references/doi.py` | `app/services/references/doi.py` | ✅ |
| 8 | `api/v1/academic.py` | `app/api/v1/academic.py` | ✅ |

Módulo adicional: `app/services/references/validator.py` (orquestrador do
relatório de validação acadêmica).

## 2. Funcionalidades concluídas

- **Modelos imutáveis de referência e citação** (`models.py`): `Author`,
  `Reference`, `Citation`, `Match`, `ReferenceType`, `CitationKind` e
  `MatchConfidence`, com verificação determinística de campos obrigatórios
  por tipo de obra (`missing_required_fields`) sem inventar metadados.
- **Extração de referências** (`parser.py`): localização da seção de
  referências e parsing de entradas bibliográficas (artigo, livro, web etc.)
  com `source_range` preservado em relação ao texto original.
- **Extração de citações NBR 10520:2023** (`citation_parser.py`): citações
  autor-data parentéticas e narrativas (incluindo verificação da regra da
  NBR 10520:2023 sobre sobrenomes em minúsculas com inicial maiúscula dentro
  dos parênteses), citações numéricas e citações diretas longas.
- **Associação citação ↔ referência** (`matcher.py`): pareamento com nível de
  confiança (`HIGH`, `MEDIUM`, `LOW`, `NONE`) e detecção de referências não
  citadas no corpo do texto.
- **Formatação ABNT NBR 6023:2025** (`nbr6023.py`): formatação determinística
  de autores (incluindo regra de mais de 3 autores / *et al.*) e entradas por
  tipo de documento, omitindo campos ausentes em vez de inventá-los.
- **Importação de BibTeX e CSL-JSON** (`bibtex.py`, `csl_json.py`): conversão
  para `Reference` com validação dos campos obrigatórios.
- **Identificação e consulta opt-in de DOI** (`doi.py`): extração de DOIs por
  expressão regular e `DOIResolver` restrito à allowlist (`api.crossref.org`),
  gerando objetos `ProposedChange` para aprovação explícita do usuário — nunca
  aplicando alterações automaticamente.
- **Validador e relatório auditável** (`validator.py` + `POST /api/v1/academic/validate`):
  cada achado (`Finding`) informa `severity`, `category`, `verdict`
  (*erro comprovado*, *possível inconsistência*, *informação não verificável*
  ou *recomendação institucional*), localização (`line`, `start`, `end`),
  mensagem e `suggested_action`.

## 3. Arquivos criados ou modificados

- **Criados (backend)**:
  `app/services/references/{models,parser,citation_parser,matcher,nbr6023,bibtex,csl_json,doi,validator}.py`,
  `app/schemas/academic.py`, `app/api/v1/academic.py`,
  `tests/unit/test_references_{models,parser,citation_parser,matcher,nbr6023,import,doi,validator}.py`,
  `tests/integration/test_academic_api.py`.
- **Modificados**: `app/services/references/__init__.py`, `app/api/router.py`
  (registro de `/api/v1/academic`), `app/main.py` (`doi_resolver` no estado da
  aplicação).
- **Documentação**: `docs/ARCHITECTURE.md` (§7.5), `docs/ROADMAP.md` (estado e
  critérios da Onda 5), `README.md` (estado e índice de relatórios),
  `docs/waves/onda-5.md`.

## 4. Testes realizados

| Suíte | Testes |
|---|---|
| Citações (`test_references_citation_parser.py`, unitário) | 7 |
| DOI (`test_references_doi.py`, unitário) | 5 |
| Importação BibTeX / CSL-JSON (`test_references_import.py`, unitário) | 5 |
| Associação citação ↔ referência (`test_references_matcher.py`, unitário) | 5 |
| Modelos (`test_references_models.py`, unitário) | 5 |
| Formatação NBR 6023:2025 (`test_references_nbr6023.py`, unitário) | 8 |
| Parser de referências (`test_references_parser.py`, unitário) | 7 |
| Validador acadêmico (`test_references_validator.py`, unitário) | 6 |
| API `/api/v1/academic/validate` (`test_academic_api.py`, integração) | 5 |
| Subtotal Onda 5 | **53** |
| Ondas 0–4 | 352 |
| **Total** | **405** |

Cobertura de `app/services/references/`: **95%** (mínimo exigido: 80%).

## 5. Resultados obtidos (com saída real dos comandos)

```
$ ruff check .
All checks passed!

$ ruff format --check .
132 files already formatted

$ mypy .
Success: no issues found in 131 source files

$ pytest --cov=app/services/references -q
405 passed in 9.81s

Name                                         Stmts   Miss  Cover
----------------------------------------------------------------
app/services/references/__init__.py             11      0   100%
app/services/references/bibtex.py               25      4    84%
app/services/references/citation_parser.py      57      1    98%
app/services/references/csl_json.py             42      4    90%
app/services/references/doi.py                  66      2    97%
app/services/references/matcher.py              25      3    88%
app/services/references/models.py               91      1    99%
app/services/references/nbr6023.py              77      5    94%
app/services/references/parser.py              115      8    93%
app/services/references/validator.py           103      5    95%
----------------------------------------------------------------
TOTAL                                          612     33    95%
```

## 6. Pendências

| Pendência | Onda | Observação |
|---|---|---|
| Exportação das referências formatadas em DOCX/PDF | 6 | `format_reference` pronto; materialização em estilos Word é da Onda 6 |
| Interface de revisão e aprovação visual de propostas de DOI | 7 | Página "Validador acadêmico" prevista na Onda 7 |
| Persistência de relatórios em `validation_reports` | 8 | Modelo/migração previstos na estabilização |

## 7. Riscos conhecidos

- **Invenção/catalogação fictícia de referência (`R-13`)**: mitigado — campos
  ausentes nunca são preenchidos com placeholders inventados; `missing_required_fields`
  reporta cada campo faltante como achado auditável.
- **SSRF em consulta de DOI**: mitigado — `DOIResolver` valida o host contra
  allowlist estrita (`api.crossref.org`), opera apenas quando
  `Settings.enable_doi_lookup=True` e `consultar_doi=True`, e jamais envia o
  conteúdo do documento (apenas o identificador DOI).
- **Aplicação silenciosa de metadados externos**: mitigado — divergências
  retornadas pelo Crossref geram achados `metadata_mismatch` com a proposta em
  `suggested_action`, preservando o texto original intacto.

## 8. Próxima onda recomendada

**Onda 6 — Geração de Documentos**: exportação em DOCX com estilos nativos do
Word, campos reais (`TOC`, `PAGE`, `NUMPAGES`, `SEQ`, `STYLEREF`, `REF`),
renderização de PDF em processo isolado, exportação TXT/Markdown e histórico de
versões. **Não iniciar sem autorização expressa.**

## 9. Limitações declaradas

1. **Parsing de referências em texto livre é heurístico**: entradas fora dos
   padrões usuais da NBR 6023 podem não ter todos os subcampos extraídos; nesses
   casos, o validador sinaliza os campos não verificados sem inventar valores.
2. **Consulta de DOI desabilitada por padrão**: requer ativação explícita em
   configuração (`enable_doi_lookup=True`) e na requisição (`consultar_doi=True`).
3. **Aprovação de propostas de DOI na UI**: a rota já entrega as propostas
   estruturadas no relatório; a interação visual de aceitar/rejeitar cada campo
   pertence à Onda 7.
