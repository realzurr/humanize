# ADR-0015 — Conformidade declarada por regra, com fonte e grau de confiança

- **Status**: Aceita
- **Data**: 2026-10-21
- **Impacto**: Alto

## Contexto

As normas ABNT são protegidas por direitos autorais e, além disso, o
produto será usado em contextos onde a **precisione da declaração de
conformidade** tem peso: bancas de defesa, comissões de exame, editoras.

Três temptacoes precisam ser evitadas:

1. **Reproduzir o texto da norma.** Ilegal e desnecessario — a estrutura e as
   regras bastam.
2. **Declarar "em conformidade com a ABNT".** Genérico demais para ser
   verificável e, em regra, falso.
3. **Codificar regra institucional como se fosse norma.** Produz
   conformidade alegada sem lastro.

## Decisão

### 1. Cada regra declara sua fonte

Toda regra de formatação, em `templates/**`, carrega metadados de origem:

```yaml
sources:
  - norm: "ABNT NBR 14724"
    edition: "2024"
    section: "5.1"
    url: "https://..."
    consulted_at: "2026-10-21"
    confidence: high
```

`confidence` ∈ {`high`, `medium`, `low`} reflete o grau de verificação da
**fonte** (norma oficial acessível, guia institucional, resumo community).

### 2. Conformidade por regra, nunca integral

O relatório de conformidade é uma lista de **regras verificadas**:

| Regra | Veredito | Fonte | Confiança |
|---|---|---|---|
| `page.margins.anverso` | conforme | NBR 14724:2024 §5.1 | high |
| `page.margins.verso` | conforme | NBR 14724:2024 §5.1 | high |
| `text.pagination.position` | conforme | NBR 14724:2024 §5.4 | high |
| `sections.numbering` | conforme | NBR 6024:2012 | medium |
| `ficha.catalografica` | **não aplicável** | — | — |
| `sumario.conteudo` | pendente | NBR 6027:2012 | low |

Vereditos possíveis: `conforme` · `nao_conforme` · `nao_aplicavel` ·
`pendente` · `nao_verificavel` · `desvio_institucional`.

Nunca existe o veredito "conforme a ABNT" como um todo.

### 3. Normas não são reproduzidas

O sistema guarda **parâmetros** (margem em cm, corpo da fonte, posição da
página) e a **referência** (norma, edição, seção, URL, data). Nenhum texto
integral de norma é armazenado no repositório.

### 4. Fontes com data

Toda consulta a fonte é datada. Uma regra cuja fonte tenha mais de N anos
(sugestão: 3) recebe confiança reduzida e sinalização de revisão.

### 5. Estado de verificação das normas

O levantamento das edições vigentes, com URLs e datas de consulta, está em
[`../standards/ABNT_NORMS_RESEARCH.md`](../standards/ABNT_NORMS_RESEARCH.md).
A Onda 4 deve revalidar antes de codificar.

## Consequências

### Positivas

- O relatório é auditável e verificável por terceiros.
- Nenhuma afirmação de conformidade sem lastro documental.
- Investimento em manuais institucionais continua útil e rastreável.
- Limites do produto ficam explícitos (ex.: sumário e campo do Word; a
  conformidade é sobre o *conteúdo*).

### Negativas

- Relatórios mais extensos e menos "vendidos" do que um selo de conformidade.
- Manter as fontes datadas e verificadas exige trabalho recorrente (a
  identificar como pendência de manutenção na Onda 8).

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|---|---|
| Declarar conformidade geral | Inverificável e frequentemente falso |
| Reproduzir a norma no repositório | Inlegal; além disso, desatualiza |
| Declarar apenas "baseado na ABNT" | Não informa regra, fonte nem desvio |
| Deixar a fonte implicita no código | Não auditável, não datável, não reportável |
