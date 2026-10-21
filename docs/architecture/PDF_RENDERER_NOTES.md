# Notas do Renderizador de PDF e Comparação DOCX ↔ PDF

- **Onda**: 6 — Geração de Documentos
- **Data**: 2026-10-21
- **Decisão associada**: [`ADR-0012`](../decisions/ADR-0012-document-export.md)
- **Módulo**: `app/services/document_export/pdf_builder.py`

---

## 1. Arquitetura de renderização

O DOCX gerado por `app/services/document_export/docx_builder.py` é a **fonte
única de verdade** para o layout acadêmico (estilos nativos do Word, margens
parametrizadas, paginação e campos OpenXML).

Para preservar paridade estrutural entre o arquivo editável (`.docx`) e o
documento de leitura/impressão (`.pdf`), o PDF é renderizado diretamente a
partir do DOCX em um **subprocesso isolado** fora do event loop assíncrono:

```
AcademicDocument + Template
        │
        ▼
   build_docx()  ──►  documento.docx (estilos nativos + campos TOC/PAGE/SEQ/REF)
                            │
                            ▼  asyncio.to_thread + subprocess.run (perfil isolado)
                      soffice --headless --convert-to pdf
                            │
                            ▼
                      compare_docx_and_pdf()  (inspeção via PyMuPDF)
```

### 1.1 Isolamento de processo e concorrência

Cada invocação do LibreOffice (`soffice --headless`) cria um diretório
temporário dedicado (`tempfile.TemporaryDirectory`) e define um perfil de
usuário exclusivo via `-env:UserInstallation=file://<tmp>/lo_profile`. Isso
evita bloqueio de lock entre requisições simultâneas e impede que falhas ou
timeouts do conversor afetem o processo da API FastAPI.

### 1.2 Comportamento na ausência do renderizador

Quando `Settings.pdf_renderer == "none"` ou o binário configurado
(`Settings.libreoffice_binary`, por padrão `soffice`) não está instalado no
sistema:

1. `build_pdf_from_docx` retorna `PdfBuildResult(available=False, content=None)`
   com a limitação declarada em `limitations` e `warnings`;
2. a API (`POST /api/v1/exports`) declara `pdf_available: false` e garante a
   entrega dos formatos determinísticos (`docx`, `txt`, `md`);
3. nenhum PDF degradado ou fictício é gerado e nenhuma falha silenciosa ocorre.

---

## 2. Verificações automáticas do comparador (`compare_docx_and_pdf`)

Após a geração do PDF, o módulo `pdf_builder.py` inspeciona o arquivo com
`pymupdf` e compara suas métricas com a inspeção XML do DOCX de origem
(`DocxInspection`):

| Dimensão verificada | Critério | Tolerância |
|---|---|---|
| Tamanho da página | Largura e altura do PDF (convertidas de pontos PostScript para cm) comparadas a `w:pgSz` do DOCX (A4 = 21,0 × 29,7 cm) | ± 0,25 cm |
| Margens do corpo | Bounding boxes (`x0`, `y1`) dos blocos textuais do corpo comparados às margens parametrizadas do anverso/verso no template | ± 0,60 cm |
| Paginação | Quantidade total de páginas (`page_count >= 1`) e páginas com conteúdo textual (`pdf_non_empty_pages >= 1`) | — |
| Quebras indevidas | Detecção de títulos numerados isolados nos últimos 2 cm úteis da página (possível título órfão) | — |

---

## 3. Diferenças e limitações conhecidas (LibreOffice vs. Microsoft Word)

1. **Atualização do campo dinâmico de sumário (`TOC`)**:
   - O DOCX armazena a instrução `{ TOC \o "1-3" \h \z \u }` e ativa
     `<w:updateFields w:val="true"/>` em `word/settings.xml`.
   - Ao abrir no Microsoft Word, o usuário é solicitado a atualizar os campos
     (ou pressiona `F9`), populando títulos e números de página exatos.
   - Na conversão direta em lote (`soffice --headless --convert-to pdf`), o
     LibreOffice pode manter o texto de espaço reservado do campo `TOC` caso
     a macro de atualização de índices não seja executada antes da exportação.
2. **Métricas tipográficas e substituição de fontes em Linux**:
   - Quando os templates especificam `Times New Roman` ou `Arial` em servidores
     Linux que não possuem o pacote `ttf-mscorefonts-installer`, o LibreOffice
     substitui metricamente por `Liberation Serif` ou `Liberation Sans`.
   - Apesar da equivalência métrica, diferenças sutis de *kerning* e
     *hinting* podem deslocar quebras de linha em textos longos.
3. **Cabeçalhos espelhados (anverso/verso)**:
   - O DOCX configura `w:mirrorMargins`, `oddAndEvenPages` e cabeçalhos
     distintos para páginas ímpares (canto superior direito) e pares (canto
     superior esquerdo) conforme a ABNT NBR 14724:2024 §5.1/§5.4.
   - Em documentos de página única, apenas o cabeçalho de primeira página (oculto
     nos elementos pré-textuais) ou de página ímpar é materializado no PDF.
