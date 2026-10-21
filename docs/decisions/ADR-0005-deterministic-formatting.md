# ADR-0005 — Formatação determinística; a LLM nunca define layout

- **Status**: Aceita
- **Data**: 2026-10-21
- **Impacto**: Alto

## Contexto

Existe uma tentação natural em usar a LLM para "formatar" o documento
("organize em capítulos, aplique margens ABNT"). Isso é errado por quatro
motivos:

1. **Não determinismo** — a mesma entrada produz saidas diferentes.
2. **Não rastreabilidade** — não há como saber por que um parágrafo foi
   movido ou por que a margem ficou diferente.
3. **Risco de perda** — a LLM pode omitir conteúdo ao reestruturar.
4. **Impossibilidade de conformidade** — a NBR 14724:2024 define margens,
   paginação, numeração e estilos de forma precisa; um modelo não é fonte de
   verdade normativa.

## Decisão

**A LLM participa apenas do conteúdo textual. Todo o layout é determinístico,
vindo de template.**

Concretamente:

- Margens, tamanho de página, espelhamento (anverso/verso): `templates/**`.
- Espacamentos, recuos, alinhamento, fonte e corpo: `templates/**`.
- Numeração progressiva de seções: `app/services/academic/numbering.py`,
  parametrizado pela NBR 6024.
- Títulos hierárquicos: `app/services/academic/styles.py`.
- Quebras de seção, quebra de página, posição da paginação: template.
- Legendas e fontes, citações longas, notas de rodapé: template.
- Campos do Word (TOC, PAGE, SEQ, STYLEREF, REF): gerados pelo exportador.

### Mecanismo de guarda

O `LLMRequest` da etapa de humanização não transporta parâmetros de layout.
Respostas do LLM são aplicadas **apenas** sobre o texto dos spans de tipo
`TEXT`/`EMPHASIS`/`STRONG`. Spans de tipo `CODE_BLOCK`, `MATH`, `EQUATION`,
`CITATION`, `TABLE` e `PRESERVED` são **intocados** pela etapa de
humanização.

Qualquer tentativa do modelo de introduzir instrução de layout é tratada
como texto e, se persistir, reportada como alerta pelo validador semântico.

## Consequências

### Positivas

- Reprodutibilidade: mesma entrada + mesmo template = mesmo documento.
- Conformidade ABNT verificable por regra, com fonte.
- Testes de regressão determinísticos.
- O usuário pode auditar exatamente qual regra produziu cada efeito.

### Negativas

- Estrutura semântica do texto (onde comeca um capítulo) precisa ser
  inferida por heuristicas determinísticas, não por LLM. A Onda 4 lidera com
  isso via `academic/structure.py`.
- Mudar a estrutura de um documento longo exige ação explicita do usuário.

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|---|---|
| LLM decide margens e paginação | Não determinístico, não auditável, não conforme a norma |
| LLM decide a hierarquia de seções | Mesmo problema, com risco de omissão de conteúdo |
| Template fixo em código (não parametrizado) | Não permite variação institucional nem versionamento das regras com fonte |
