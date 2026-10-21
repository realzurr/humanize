# Onda 6 — Geração de Documentos

- **Data**: 2026-10-21
- **Escopo**: exportação acadêmica em DOCX com estilos e campos nativos do Word
  (`TOC`, `PAGE`, `NUMPAGES`, `SEQ`, `STYLEREF`, `REF`), renderização de PDF a
  partir do DOCX em subprocesso isolado com comparador estrutural DOCX ↔ PDF,
  exportação TXT/Markdown, pré-visualização e histórico de versões.
- **Status**: concluída.

---

## 1. Escopo executado

| # | Entregável do ROADMAP | Onde | Estado |
|---|---|---|---|
| 1 | `document_export/docx_builder.py` | `app/services/document_export/docx_builder.py` | ✅ |
| 2 | `document_export/fields.py` | `app/services/document_export/fields.py` | ✅ |
| 3 | `document_export/pdf_builder.py` | `app/services/document_export/pdf_builder.py` | ✅ |
| 4 | `document_export/writer.py` (TXT, Markdown, prévia e histórico) | `app/services/document_export/writer.py` | ✅ |
| 5 | `api/v1/exports.py` + `schemas/exports.py` | `app/api/v1/exports.py`, `app/schemas/exports.py` | ✅ |
| 6 | Documentação de diferenças do renderizador PDF | `docs/architecture/PDF_RENDERER_NOTES.md` | ✅ |

## 2. Funcionalidades concluídas

- **Campos dinâmicos OpenXML reais** (`fields.py`): inserção e extração de
  campos complexos do Word (`TOC`, `PAGE`, `NUMPAGES`, `SEQ`, `STYLEREF`,
  `REF`), criação de marcadores (`w:bookmarkStart`/`w:bookmarkEnd`) para
  referências cruzadas e ativação de `<w:updateFields w:val="true"/>` em
  `word/settings.xml`.
- **Construção de DOCX com estilos nativos do Word** (`docx_builder.py`):
  configuração determinística de `Normal`, `Heading 1..4`, `Citacao Longa`,
  `Legenda`, `Fonte`, `Referencia`, `Sem Indicativo`, `Nota Rodape` e `Codigo`
  a partir das regras parametrizadas do template resolvido (incluindo sobreposições
  institucionais como UFMS/UFGD).
- **Configuração de página A4, margens espelhadas e paginação** (`docx_builder.py`):
  aplicação das margens do anverso e do verso conforme `resolve_margins`,
  cabeçalhos diferenciados para páginas pares/ímpares com campo `PAGE` e
  ocultação de numeração na primeira página pré-textual.
- **Elementos pré-textuais, ficha catalográfica reservada e sumário TOC real**:
  capa e folha de rosto alinhadas por estilo/parágrafo (nunca por espaços ou
  tabulações repetidas), espaço da ficha catalográfica **estritamente
  reservado** (sem dados fictícios) e sumário inserido como instrução
  `TOC \o "1-3" \h \z \u`.
- **Inspeção estrutural XML do DOCX** (`inspect_docx`): verificação de
  `word/styles.xml`, `word/document.xml` e `word/settings.xml`, comprovando a
  presença dos estilos nativos, dos campos `TOC` e `PAGE`, a reserva da ficha
  catalográfica e a ausência de simulação de alinhamento por espaços ou
  tabulações repetidas.
- **Renderização de PDF em processo isolado e comparador DOCX ↔ PDF**
  (`pdf_builder.py`): invocação de `soffice --headless --convert-to pdf` via
  `asyncio.to_thread` com diretório de perfil isolado (`-env:UserInstallation`),
  inspeção do PDF via `pymupdf` (`compare_docx_and_pdf`: validação de tamanho
  A4, margens, paginação e títulos órfãos) e fallback explícito para
  DOCX/TXT/Markdown quando o renderizador não está disponível.
- **Exportadores TXT e Markdown, pré-visualização e histórico de versões**
  (`writer.py` + `api/v1/exports.py`): geração de `.txt` e `.md`,
  pré-visualização estruturada (`POST /api/v1/exports/preview`), persistência
  em disco com hash SHA-256, versionamento incremental, retenção configurável e
  rotas de listagem, detalhe, download e histórico por documento.

## 3. Arquivos criados ou modificados

- **Criados (backend)**:
  `app/services/document_export/{fields,docx_builder,pdf_builder,writer}.py`,
  `app/schemas/exports.py`, `app/api/v1/exports.py`,
  `tests/unit/test_export_{fields,docx_builder,pdf_builder,writer}.py`,
  `tests/integration/test_exports_api.py`.
- **Modificados (backend)**:
  `app/services/document_export/__init__.py`, `app/api/router.py` (registro de
  `exports.router`), `app/main.py` (`app.state.export_store`).
- **Documentação**:
  `docs/architecture/PDF_RENDERER_NOTES.md`, `docs/ARCHITECTURE.md` (§7.6),
  `docs/ROADMAP.md` (estado e critérios da Onda 6), `README.md` (estado e
  índice de relatórios), `docs/waves/onda-6.md`.

## 4. Testes realizados

| Suíte | Testes |
|---|---|
| Campos OpenXML do Word (`test_export_fields.py`, unitário) | 3 |
| Construtor e inspetor DOCX (`test_export_docx_builder.py`, unitário) | 4 |
| Renderizador PDF e comparador DOCX↔PDF (`test_export_pdf_builder.py`, unitário/integração) | 5 |
| Exportadores TXT/MD, prévia e histórico (`test_export_writer.py`, unitário) | 3 |
| API `/api/v1/exports` (`test_exports_api.py`, integração) | 3 |
| Subtotal Onda 6 | **18** |
| Ondas 0–5 | 405 |
| **Total** | **423** |

Cobertura de `app/services/document_export/`: **95%** (mínimo exigido: 80%).

## 5. Resultados obtidos (com saída real dos comandos)

```
$ ruff check .
All checks passed!

$ ruff format --check .
143 files already formatted

$ mypy .
Success: no issues found in 142 source files

$ pytest --cov=app/services/document_export -q
423 passed in 14.21s

Name                                           Stmts   Miss  Cover
------------------------------------------------------------------
app/services/document_export/__init__.py           6      0   100%
app/services/document_export/docx_builder.py     536     23    96%
app/services/document_export/fields.py            88      0   100%
app/services/document_export/pdf_builder.py      119     11    91%
app/services/document_export/writer.py           297     18    94%
------------------------------------------------------------------
TOTAL                                           1046     52    95%
```

## 6. Pendências

| Pendência | Onda | Observação |
|---|---|---|
| Página visual de Exportação e Histórico no frontend | 7 | Rotas `/api/v1/exports` e `/api/v1/exports/preview` prontas |
| Persistência de `exports` e `revisions` em banco SQLAlchemy/Alembic com isolamento `owner_id` | 8 | Hoje mantido em `ExportHistoryStore` + disco (`export_dir`) |

## 7. Riscos conhecidos

- **Divergência entre PDF (LibreOffice) e DOCX (Word) (`R-10`)**: mitigado —
  documentado em `docs/architecture/PDF_RENDERER_NOTES.md` e verificado pelo
  comparador automático `compare_docx_and_pdf` (tamanho de página, margens,
  paginação e quebras indevidas).
- **Sumário só aparece paginado após atualizar campo no Word (`R-11`)**:
  mitigado — `w:updateFields` é ativado em `settings.xml` e a resposta da API
  inclui aviso orientando a atualização de campos (`F9`).
- **Ficha catalográfica fictícia (`R-13`)**: mitigado — o bloco
  `catalog_record` gera exclusivamente a nota de reserva institucional e
  `inspect_docx` valida que nenhum ISBN/CDD/CDU fictício foi inserido.

## 8. Próxima onda recomendada

**Onda 7 — Interface e Experiência do Usuário**: implementação das 11 páginas
da SPA React + TypeScript (Dashboard, Editor, Normalização, Humanização
semântica, Comparação de versões, Templates ABNT, Validador acadêmico,
Histórico, Perfis autorais, Configurações de LLM e Exportação) e testes E2E
com Playwright. **Não iniciar sem autorização expressa.**

## 9. Limitações declaradas

1. **Dependência externa para PDF**: a geração de PDF depende do binário
   `soffice` (LibreOffice). Quando ausente ou desativado (`pdf_renderer="none"`),
   a API declara a limitação em `limitations` e entrega apenas DOCX, TXT e
   Markdown.
2. **Atualização do campo TOC em modo headless**: o campo `TOC` é gravado como
   instrução nativa do Word; na conversão direta headless sem macro de
   atualização de índice, o PDF exibe o texto orientativo de atualização de
   campos.
3. **Armazenamento do histórico em memória + sistema de arquivos**: a
   persistência relacional multiusuário com autenticação e controle de acesso
   pertence à Onda 8.
