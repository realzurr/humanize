# ADR-0003 — Documento intermediário (IR) próprio como contrato central

- **Status**: Aceita
- **Data**: 2026-10-21
- **Impacto**: Alto

## Contexto

O pipeline tem 10 estágios que operam sobre o mesmo conteúdo: normalização,
estruturação, proteção, humanização, validação semântica, revisão, template,
formatação, validação acadêmica e exportação.

Sem um modelo intermediário, cada estágio operaria sobre texto solto
(`str`), o que causaria:

- perda de proveniência (impossível dizer de onde veio um trecho);
- impossibilidade de preservar blocos atômicos (tabelas, equações, código);
- impossibilidade de mascarar e restaurar entidades de forma confiável;
- diff frágil (comparação de strings) em vez de diff de trechos.

## Decisão

Criar um **documento intermediário próprio** em `backend/app/ir/`, com quatro
módulos:

### `app/ir/spans.py` — trechos inline

`InlineSpan(id, kind, text, source_range, attributes, protected_ids)`.

- `SpanKind` distingue `TEXT`, `EMPHASIS`, `STRONG`, `CODE_INLINE`,
  `CODE_BLOCK`, `MATH`, `EQUATION`, `LINK`, `CITATION`, `FOOTNOTE_REF`,
  `QUOTE`, `PRESERVED`, `FIELD`, `LINE_BREAK`, `TAB`.
- `InlineSpan.is_lossless_target` marca os trechos que **nunca** podem ser
  reescritos automaticamente.
- A lista de spans e **plana** (não uma árvore): permite fatiar e remontar o
  texto com offsets estáveis durante a fase de máscara.
- `SourceRange` usa **code points** Unicode, não bytes nem unidades UTF-16,
  para que Python e TypeScript produzam os mesmos offsets.

### `app/ir/blocks.py` — blocos estruturais

`BlockKind` cobre pré-textuais, textuais, pos-textuais e auxiliares.
`PAGE_BREAK_BLOCKS` marca os blocos que iniciam em página nova por regra
geral. `TableData` preserva tabelas como unidade atomica.

### `app/ir/protection.py` — catálogo de entidades protegidas

`ProtectedKind` (17 categorias), `ProtectedEntity` (com `level` de
protegicao e `fingerprint`), `ProtectionCatalog` (com `missing_fingerprints`
e `changed_fingerprints`).

### `app/ir/document.py` — documento e metadados

`AcademicDocument` (imutável, com `original_text`, `revisions` append-only e
`current_revision_id`), `DocumentRevision`, `DocumentMetadata`,
`Transformation`.

### Invariantes

1. Todos os modelos usam `model_config = ConfigDict(frozen=True)`.
2. `original_text` nunca é sobrescrito.
3. `with_revision()` devolve uma **cópia**; o objeto original não é mutado.
4. `source_range` é sempre relativo ao **original**, nunca a revisão corrente.

## Consequências

### Positivas

- Cada etapa é auditável: sabe-se exatamente de onde veio cada trecho.
- A máscara de entidades protegidas é confiável: os spans correspondem a
  fatias contiguas do texto.
- O diff lado a lado do frontend passa a ser por trecho, não por
  comparação de string.
- Tabelas, equações e código são transportados sem remontagem.

### Negativas

- Mais código de infraestrutura antes da primeira funcionalidade visível.
- `source_range` exige que cada estágio mantenha a ligação com o original —
  trabalho extra que, sem ele, seria impossível.

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|---|---|
| Usar apenas `str` entre estágios | Perde proveniência, proteção e diff estruturado |
| Usar AST de Markdown | Não representa documento acadêmico (capa, sumário, referências) |
| Usar `python-docx` como IR | Acopla o domínio ao formato DOCX; precludes TXT/Markdown e leitura de PDF |
| Usar um formato intermediário externo (JSON Schema) | Serializacao a cada etapa; perde identidade e imutabilidade em memória |
