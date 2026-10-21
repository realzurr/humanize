# ADR-0009 — Catálogo de entidades protegidas e máscara antes da LLM

- **Status**: Aceita
- **Data**: 2026-10-21
- **Impacto**: Alto

## Contexto

A humanização semântica é a etapa em que o texto do autor passa por um modelo
de linguagem. A especificação é explicita: "Não suprimir informação
cientifica", "Números e resultados só mudam com sinalização explicita e
aprovação do usuário", "A LLM não devera inventar autores, artigos, DOI,
resultados, estatísticas ou fontes bibliograficas".

Modelos de linguagem **alteram números**. E uma falha frequente e silenciosa:
"45%" virá "45,5%", "estatisticamente significativo" virá "comprovadamente
significativo", um DOI é reescrito com um caractere trocado. Em um trabalho
acadêmico, cada um desses erros pode invalidar um argumento.

## Decisão

Implementar a proteção em **três momentos** distintos, com um catálogo
central em `app/ir/protection.py`.

### 1. Extração (etapa `PROTECT`)

O extrator identifica 17 categorias de entidade no IR e as registra em
`ProtectionCatalog`:

`NUMBER` · `DATE` · `CITATION` · `REFERENCE` · `DOI` · `URL` · `FORMULA` ·
`TERM_DEFINED` · `PERSON` · `INSTITUTION` · `STATISTIC` · `TABLE_ID` ·
`FIGURE_ID` · `CODE` · `QUOTE_LITERAL` · `UNIT` · `SPECIMEN`

Cada `ProtectedEntity` carrega:

- `level` de proteção: `CRITICAL` | `HIGH` | `MEDIUM` | `LOW`;
- `fingerprint`: hash do valor **normalizado** (NFKC, separadores de milhar e
  decimal unificados, sinais de menos unificados, espaços internos removidos);
- `source_range` relativo ao original;
- `rule_id` e `confidence` da detecção.

### 2. Máscara (antes da chamada ao LLM)

Cada entidade é substituida por um **placeholder estável** (`<P0042>`), e o
texto mascarado é o que vai ao provedor. O placeholder:

- tem formato reconhecível e não-natural, para reduzir a chance de o modelo
  "corrigi-lo";
- nunca é interpretado como texto a ser estilizado;
- é reversível de forma exata.

### 3. Validação (após a resposta)

- **Restauração**: toda entidade que o LLM reproduziu é restaurada com o
  valor **original** (não o do modelo).
- **Detecção de perda**: `catalog.missing_fingerprints(revised)` identifica
  entidades que sumiram.
- **Detecção de alteração**: entidades cujo valor mudou são registradas como
  `changed`.
- **Detecção de invenção**: números presentes na revisão e ausentes do
  original são sinalizados (possível resultado inventado).

### 4. Bloqueio de aprovação

Ver `ADR-0013`: perda de entidade `CRITICAL` **impede** a aprovação
automática.

### 5. Limites do fingerprint

O fingerprint é usado **apenas para comparação**; nunca reescreve o valor
exibido. A normalização de separadores segue a heuristica:

| Entrada | Normalizada | Regra |
|---|---|---|
| `1.000` | `1000` | exatamente 3 dígitos após o separador => milhar |
| `45,5%` | `45.5%` | demais separadores entre dígitos => decimal canônico |
| `-5` (U+2212) | `-5` | unifica sinais de menos |
| `1 234` | `1234` | remove espaços internos |

Ambiguidade aceita é documentada: `1.000` pode significar `1.0` em texto em
inglês. O produto opera em pt-BR, onde a leitura de milhar e dominante.

## Consequências

### Positivas

- Números, datas, DOI, fórmulas e citações sobrevivem ao ciclo de humanização.
- O usuário ve **exatamente** o que mudou em termos de dado verificável.
- O relatório de conformidade ganha a seção "dados protegidos", com a
  rastreabilidade exigida pela especificação.

### Negativas

- A detecção é **heuristica** (regex + contexto). Falsos negativos são
  possíveis — por isso o relatório também lista o que *não* foi possível
  verificar.
- Mascar reduz a fluidez do texto enviado ao modelo, o que pode degradar
  ligeiramente a qualidade da reescrita. A solução adotada: mascarar apenas o
  que é crítico e preservar a estrutura da frase.

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|---|---|
| Confiar no prompt ("não altere números") | Não é confiável; o modelo altera mesmo assim |
| Validar só por diff de texto | Não distingue mudança legitima de mudança de dado |
| Reverter a reescrita se o modelo mudar algo | Descarta trabalho legítimo; não é granular |
| Usar o modelo para extrair as entidades | Circular e caro; regex + contexto são mais baratos e determinísticos |
