# ADR-0016 — `pymupdf` como dependência opcional (licenciamento AGPL)

- **Status**: Aceita
- **Data**: 2026-10-22
- **Impacto**: Médio
- **Supersede**: — (complementa `ADR-0014`)

## Contexto

O projeto é distribuído sob a **MIT License** (`ADR-0014`). A inspeção e a
comparação estrutural do PDF gerado (`compare_docx_and_pdf`) dependia de
**PyMuPDF** (`pymupdf`), biblioteca licenciada sob **AGPL-3.0**, declarada como
dependência obrigatória em `pyproject.toml`. Uma dependência obrigatória
AGPL-3.0 em um produto MIT pode contaminar o licenciamento do todo, ainda que
o uso seja apenas interno (inspeção, não redistribuição do código).

A auditoria de qualidade (QA) classificou isso como **GAP-09** — risco de
licenciamento aberto que deveria ter sido resolvido antes da estabilização.

## Decisão

1. **Tornar `pymupdf` uma dependência opcional** (extra `pdf`), removida de
   `dependencies`:
   ```toml
   [project.optional-dependencies]
   pdf = ["weasyprint>=62.3", "pymupdf>=1.24"]
   ```
2. **Importar `pymupdf` de forma lazy** em
   `app/services/document_export/pdf_builder.py`, com **degradação graciosa**:
   quando a biblioteca não está instalada, `compare_docx_and_pdf` devolve um
   `PdfComparisonReport` com a limitação declarada, sem falha silenciosa nem
   import obrigatório.
3. **Documentar** a limitação: sem `pymupdf`, o PDF ainda é gerado pelo
   LibreOffice, mas a **comparação estrutural** (tamanho, margens, paginação)
   fica indisponível — comportamento explicitado na resposta da API.

## Consequências

### Positivas

- O núcleo do produto (DOCX/TXT/Markdown/PDF via LibreOffice) permanece
  totalmente funcional sob MIT sem nenhuma dependência copyleft forte.
- Quem instalar o extra `pdf` (para inspeção/validação de PDF) o faz de forma
  consciente e isolada do núcleo.

### Negativas

- Sem `pymupdf`, a comparação DOCX↔PDF automática não é executada; a limitação
  precisa ser comunicada ao usuário (já previsto no fluxo de limitações).

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|---|---|
| Manter `pymupdf` obrigatório | Risco de contaminação AGPL em produto MIT |
| Remover a comparação de PDF | Perde a validação de margens/paginação do `ADR-0012` |
| Substituir por outra biblioteca | `pypdf`/`pdfplumber` são BSD/MIT, mas exigem reescrita; pode ser reavaliado como pendência |
