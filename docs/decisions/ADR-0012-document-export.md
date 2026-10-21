# ADR-0012 — Exportação DOCX nativa primeiro; PDF em processo isolado

- **Status**: Aceita
- **Data**: 2026-10-21
- **Impacto**: Alto

## Contexto

O critério de aceitação da Onda 6 exige: "Exportar documentos que possam ser
editados no Word e visualizados corretamente em PDF".

Isso impõe duas restrições técnicas:

1. **O DOCX precisa usar mecanismos reais do Word** — estilos nativos, campos
   `TOC`/`PAGE`/`SEQ`/`STYLEREF`/`REF`, numeração de listas vinculada a
   estilos. Simular alinhamento com espaços e tabulações repetidas produz
   um documento que *parece* correto mas quebra em qualquer edição, câmbio
   de fonte ou impressão.
2. **O PDF precisa bater com o DOCX.** O caminho mais fiel é renderizar o
   próprio DOCX (o que o Word faz), em vez de reimplementar o layout em
   outro motor.

## Decisão

### DOCX (fonte única de verdade)

- `python-docx` para construção; `docxtpl` quando houver necessidade de
  template DOCX.
- Estilos nativos do Word criados e reutilizados (`Heading 1..4`, `Normal`,
  `Citacao Longa`, `Fonte`, `Legenda`, `Referencia`).
- Campo de sumário **real** (`{ TOC \o "1-3" \h \z \u }`), não texto
  digitado. O sumário só aparece após a atualização de campos pelo Word (ou
  pelo LibreOffice) — limitação a ser comunicada na interface.
- Numeração progressiva de seções por lista vinculada a estilos, alinhada a
  NBR 6024.
- Cabeçalho, rodapé e paginação conforme o template (posição diferenciada
  para anverso/verso).
- Imagens e tabelas preservadas; tabelas como unidade atomica.
- `PyMuPDF` para inspeção estrutural e validação do PDF resultante.

### PDF (renderizado a partir do DOCX)

- Renderizador padrão: **LibreOffice** (`soffice --headless --convert-to
  pdf`), invocado como **subprocesso isolado**, nunca no event loop.
- Alternativas configuráveis: `docx2pdf` (Windows/macOS) ou `none`.
- **Sem renderizador disponível**, a limitação é **declarada** na resposta da
  API e na interface; apenas DOCX, TXT e Markdown são gerados. O sistema
  nunca falha silenciosamente nem produz um PDF degradado sem avisar.
- As diferencas conhecidas entre o renderizador e o Word são documentadas em
  `docs/architecture/PDF_RENDERER_NOTES.md` e verificadas por comparador
  automático (número de páginas, tamanho de página, margens, presença de
  quebras indevidas).

### História de versões

Cada exportação registra: formato, hash do arquivo, tamanho, revisão de
origem e timestamp. Exports antigos são expirados conforme a política de
retenção (`document_retention_days`).

## Consequências

### Positivas

- O DOCX é realmente editável no Word, com estilos navegáveis e sumário
  atualizável.
- O PDF nasce do DOCX, minimizando divergência.
- A limitação de ausência de renderizador é explicita, nunca silenciosa.

### Negativas

- Dependência de binário externo (LibreOffice) no ambiente de produção.
- O sumário aparece vazio até a atualização de campos — fricção de UX que
  exige orientação na interface.
- Divergências entre LibreOffice e Word em detalhes tipográficos são
  inevitáveis e precisam ser documentadas.

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|---|---|
| Gerar PDF a partir de HTML/CSS (WeasyPrint) | Layout completamente diferente do DOCX; quebra a promessa de paridade |
| Somente PDF | Descarta a exigência de DOCX editável |
| Somente DOCX | Descarta a exigência de PDF |
| `python-docx` escrevendo XML de layout a mão | Excessivamente frágil; `python-docx` + estilos nativos cobre o caso |
| Renderizar PDF no event loop | Bloqueia o event loop; viola a regra de I/O |
