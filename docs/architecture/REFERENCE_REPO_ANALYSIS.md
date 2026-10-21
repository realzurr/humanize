# Análise do Repositório de Referência — `takumar-x/AI-Humanizer`

- **Repositório**: <https://github.com/takumar-x/AI-Humanizer>
- **Análise**: Onda 0, 2026-10-21
- **Método**: clone local (`--depth 1`), leitura integral do `index.html`
  (1080 linhas) e do `LICENSE` (674 linhas), inspeção do histórico Git.
- **Decisão resultante**: [`ADR-0001`](../decisions/ADR-0001-clean-room-reimplementation.md)

---

## 1. Resumo

| Aspecto | Constatação |
|---|---|
| Tipo | Ferramenta web client-side de limpeza de texto |
| Arquivos versionados | **3** — `LICENSE`, `README.md`, `index.html` |
| `index.html` | 1080 linhas (HTML + CSS + JS vanilla, sem build) |
| Dependências | **Nenhuma** — funciona offline, sem rede |
| Licença | **GNU GPL v3** (arquivo íntegro) |
| Aviso de copyright | **Ausente** — ver §2.2 |
| Commits | 9 · branches: 1 (`main`) · tags: nenhuma |
| Estrelas / forks / issues | 3 / 0 / 0 |
| Licença declarada no README | "GPL-3.0 license" |
| Idioma da UI | EN, DE, ES, FR, PT, UK (commit mais recente) |
| Commit mais recente | `ed6b78c` — *"feat: translate UI to English and add multi-language support"* (2026-07-26) |
| Autor do commit | `takumar-x <mikhail.medvedev@gmail.com>` |

---

## 2. Licença e implicações

### 2.1 A licença

O `LICENSE` é o texto **íntegro e não modificado** da GNU General Public
License, versão 3, de 29 de junho de 2007.

A GPL-3.0 é uma licença **copyleft forte**. Suas implicações para este
projeto:

| Ação sobre o código original | Consequência sob GPL-3.0 |
|---|---|
| Copiar, traduzir, adaptar, ou usar como base | Obra derivada → distribuição **tem de** ser sob GPL-3.0, com o código-fonte completo |
| Incorporar em um produto fechado | **Proibido** |
| Executar como serviço não distribuído | Não há contágio (a GPL não é copyleft de rede) |
| Usar como biblioteca dynamically linked | Possível via LGPL, mas o arquivo é GPL-3.0 puro |

Como o produto é previsto para uso institucional/comercial, aIncorporação
direta tornaria a **opção proprietária inexistente**.

### 2.2 Observação de conformidade do repositório de origem

O `LICENSE` do upstream é o modelo GPL **sem** a linha de copyright do
projeto. O trecho canônico do modelo permanece como placeholder:

```
Copyright (C) <year>  <name of author>
```

O `index.html` **não** contém cabeçalho SPDX, nem menção a licença,
copyright ou autor. Consequência prática: **o titular do direito autoral
sobre o `index.html` não é identificável a partir dos arquivos versionados** —
a GPL-3.0, no seu artigo 1, exige que o licensee mantenha o aviso de
copyright. Isso:

- é um problema **do repositório de origem**, não nosso;
- significa que "pedir permissão" ao autor seria processo lento e de
  resultado incerto;
- reforça a decisão de não incorporar o código.

### 2.3 Decisão

**Reimplementação *clean-room*** dos requisitos funcionais, sem copiar,
traduzir ou adaptar o código. Ver [`ADR-0001`](../decisions/ADR-0001-clean-room-reimplementation.md).

Justificativa resumida:

1. A funcionalidade exigida (normalização Unicode, remoção de invisíveis,
   limpeza de Markdown, remoção de emoji) é **trivialmente reimplementável**
   a partir do padrão Unicode e dos requisitos — sem valor diferencial no
   código original.
2. O upstream tem baixa atividade, zero issues, zero forks e um único
   mantenedor — dependência arriscada.
3. O upstream **não atende** aos requisitos acadêmicos do produto (§6), o
   que exigiria reescrever a maior parte dele de qualquer forma.
4. Reimplementar elimina o contágio copyleft e preserva a liberdade de
   escolha de licença.

### 2.4 Uso permitido do repositório de referência

- Como **fonte de requisitos funcionais** (catálogo de transformações).
- Como **oracle comparativo** em teste: o motor novo da Onda 1 pode ser
  confrontado com o comportamento antigo em textos acadêmicos, **exatamente
  para detectar** as regressões descritas em §6.
- Como **documentação** (este arquivo).

**Não** é usado como código-fonte, base de derivação ou dependência.

---

## 3. Arquitetura do original

```
index.html
├── <style>          tema escuro, layout responsivo (grid 1→2 colunas)
├── <body>           2 <textarea> (entrada/saída) + KPIs + checkboxes
└── <script>         IIFE com todo o estado e a lógica
```

Estado global: `currentLang` (idioma da UI), `currentStats` (array de
`[chave, contagem]`).

Fluxo: `input` → `debounce(420ms)` → `processText()` → `sanitizeText()` →
atualiza `<textarea>` de saída + KPIs → escrita em `localStorage` apenas do
**idioma** (`app_lang`). Sem segredos, sem rede.

Nenhuma requisição HTTP, nenhum armazenamento de conteúdo, nenhum upload.

---

## 4. Inventário de transformações

Todas as transformações estão em `sanitizeText(input, opts)`
(`index.html:711-864`). As opções são apenas três: `nfkc`, `emoji`, `md`.

| # | Chave de stat | Transformação | Regex / lógica | Risco acadêmico |
|---|---|---|---|---|
| 1 | `htmlEntities` | Decodifica entidades HTML (`&amp;`, `&#x41;`, …) | `decodeEntities()` (`:694`) | Médio |
| 2 | `crlf` | `\r\n`/`\r`/U+2028/U+2029 → `\n` | `:729` | Baixo |
| 3 | `nfkc` | Normalização Unicode NFKC (com proteção de `№` e `™`) | `:731-739` | **Alto** — ver §6.1 |
| 4 | `zwc` | Remove U+00AD, U+200B–200F, U+202A–202E, U+2060–2064, U+2066–2069, U+FEFF, U+180E, U+FE00–FE0F | `:741-744` | Baixo (exceto U+00AD) |
| 5 | `nbsp` | U+00A0, U+2000–200A, U+202F, U+205F, U+3000 → espaço | `:746-749` | Baixo |
| 6 | `ansi` | Remove sequências de escape ANSI | `:751-754` | Baixo |
| 7 | `ctrl` | Remove C0 (exceto TAB/LF) e C1 | `:756-759` | Baixo |
| 8 | `dash` | U+2010–U+2015 e **U+2212** → `-` | `:762-764` | **Alto** — ver §6.2 |
| 9 | `frac` | U+2044 → `/` | `:766-769` | Baixo |
| 10 | `quotesDbl` | U+201C/201D/201E, U+00AB, U+00BB → `"` | `:771-774` | Médio |
| 11 | `quotesSng` | U+2018/2019/201A/201B, U+2039, U+203A → `'` | `:776-779` | Médio |
| 12 | `ellipsis` | U+2026 → `...` | `:781-784` | Baixo |
| 13 | `bullets` | U+2022, U+25E6, U+00B7, U+2219, U+2043, U+2027 → `-` | `:786-789` | Baixo |
| 14 | `mdHStart` | Remove `#` de títulos Markdown | `:792-794` | Médio |
| 15 | `mdHEnd` | Remove `#` final de títulos | `:796-798` | Baixo |
| 16 | `mdQuoteMk` | Remove `>` de blockquote | `:800-802` | Médio |
| 17 | `mdStarBul` | `*`/`+` no início de linha → `-` | `:804-806` | Baixo |
| 18 | `mdBoldD` / `mdItalD` | Remove `**`/`*` | `:808-817` | **Alto** — ver §6.3 |
| 19 | `mdBoldU` / `mdItalU` | Remove `__`/`_` | `:808-817` | **Alto** — ver §6.3 |
| 20 | `mdCodeSpan` | Remove crases de código inline | `:819-821` | Médio |
| 21 | `mdDeco` | Remove linhas `---`, `***`, `===` | `:823-825` | Baixo |
| 22 | `mdLoneStars` | Remove `*` isolado | `:827-829` | Baixo |
| 23 | `boxCnt` | Pseudo-gráficos de caixa → `+ - |` e espaço | `:632-654`, `:832-834` | **Alto** — ver §6.4 |
| 24 | `escDollar` | `\$` → `$` | `:836-838` | Baixo |
| 25 | `emojiCount` | Remove emoji (`\p{Extended_Pictographic}`) | `:656-661`, `:840-844` | **Alto** — ver §6.5 |
| 26 | `puncSpaceCount` | Remove espaço antes de `.,!?;:` | `:846-848` | Baixo |
| 27 | `runs` | 2+ espaços → 1 | `:850-852` | Baixo |
| 28 | (sem stat) | Remove espaços em volta de `\n` | `:854` | Baixo |
| 29 | `manyBlank` | 3+ linhas em branco → 2 | `:856-858` | Baixo |
| 30 | (sem stat) | Remove espaços no fim da linha; `trim()` final | `:860-861` | Baixo |

### 4.1 Regras de idempotência

As regras são aplicadas em sequência fixa, sem pipeline. A **ordem importa**:
por exemplo, o `NFKC` roda **antes** da remoção de invisíveis e da limpeza de
Markdown, de modo que formas compostas (ex.: `` precedido de variação
seletora) são normalizadas antes de serem limpas.

Note que a remoção de emoji ocorre **depois** do NFKC — o que é correto, pois
o NFKC pode expor caracteres que o regex de emoji não alcançaria.

---

## 5. Comportamento da interface original

Recursos notáveis que a interface nova **deve** ter (o produto alvo é mais
amplo, mas o original acertou estes pontos):

- Processamento ao vivo com `debounce` de 420 ms.
- Contadores de caracteres em entrada e saída.
- KPIs com a contagem por tipo de transformação.
- Botão de copiar com fallback para `execCommand('copy')`.
- Download de `.txt` via `Blob` + `URL.createObjectURL`.
- Alternância de idioma persistida em `localStorage` (apenas o idioma).
- Limpeza com `Ctrl+Enter` / `Cmd+Enter`.

---

## 6. Regressões identificadas

Estas são as falhas do original **para texto acadêmico**. Elas são a razão
principal de não simplesmente portar o código. Cada uma tem de ser
coberta por teste de regressão na Onda 1.

### 6.1 NFKC destrói notação científica — **crítico**

`NFKC` é uma normalização de *compatibilidade*: ela decompõe caracteres que
têm representação "equivalente". Em notação científica isso é destrutivo:

| Entrada | NFKC | Consequência |
|---|---|---|
| `10⁻⁶` | `10-6` | **Erro de ordem de grandeza** (10⁻⁶ ≠ 10−6) |
| `x²` | `x2` | Perde o quadrado |
| `H₂O` | `H2O` | Perde o subscrito (o `₂` é sub, o `²` é sup) |
| `Na⁺` | `Na+` | Perde a carga iônica |
| `CO₂` | `CO2` | Perde o subscrito |
| `m²` | `m2` | Perde a unidade de área |
| `℃` | `°C` | Aceitável |
| `№` | `No` | Aceitável |
| `ﬁ` | `fi` | Aceitável |

> O original **proíbe** NFKC apenas para `№` (U+2116) e `™` (U+2122), e
> mesmo assim `™` é removido em seguida pela remoção de emoji (§6.5).

**Mitigação no projeto:** `norm.unicode.nfkc` **desligada por padrão**, ou
operando com lista de exceções explícita (superíndices, subscritos, alfabeto grego,
símbolos matemáticos). Teste de regressão obrigatório com `10⁻⁶`, `x²`,
`Na⁺`, `CO₂` e `m²`.

### 6.2 O sinal de menos matemático é destruído — **crítico**

`index.html:762-764` converte U+2010–U+2015 **e U+2212** (MINUS SIGN) em
`-` (HYPHEN-MINUS). U+2212 é o sinal usado em equações e é
tipograficamente distinto do hífen: `a − b` (aritmético) vs. `a-b`
(intervalo/hífen). Perder a distinção em expressões é erro semântico
potencial.

**Mitigação:** a regra de traços deve excluir U+2212, ou tratar U+2212 como
entidade protegida.

### 6.3 A limpeza de Markdown come subscritos e sublinhados — **crítico**

As regexes de ênfase (`index.html:663-680`):

```js
const L = '(?<![\\p{L}\\p{N}])', R = '(?![\\p{L}\\p{N}])';
italUnd: new RegExp(L + '_(\\S(?:[^_\\n]*?)\\S)?_' + R, 'gu')
```

Exigem um caractere **não alfanumérico** antes e depois do par de `_`. Isso
protege `x_1` (o `x` é alfanumérico), **mas não**:

- `media _temperatura_` → `media temperatura` (perda de marcação) — aceitável
  como intenção;
- `X _1` → `` (o ` _1` isolado: `\S` casa `1`, mas é preciso **dois** `_`;
  neste caso só há um, então sobrevive) — ok;
- `F _i_ e _j_` → `F i e j` — **perda real**: subíndices de equação
  Destroyed;
- `__` (negrito) exige o mesmo contexto.

O caso mais perigoso é quando o texto acadêmico usa ` _` com espaço, padrão
comum em subíndices e em notação de variáveis: `Y _1`, `x _i`.

**Mitigação:** `norm.markdown` só pode ser aplicada **fora de trechos
protegidos**, e o detector de subscritos deve reconhecer `letra + espaço +
_ + subscrito`.

### 6.4 Setas de reação química viram `>` — **crítico**

`index.html:648-651`:

```js
m['\u2192'] = '>';  // →
m['\u2190'] = '<';  // ←
m['\u2191'] = '^';  // ↑
m['\u2193'] = 'v';  // ↓
```

A regra de pseudo-gráficos (§4, item 23) inclui essas quatro setas. Em
química e bioquímica, `→` indica **produto** e `⇌` indica equilíbrio.
Converter para `>` destrói a semântica da equação.

**Mitigação:** a regra de pseudo-gráficos não deve alcançar a faixa
`U+2190–U+21FF` (setas), que deve ser tratada como entidade protegida.

### 6.5 A remoção de emoji apaga `©`, `®` e `™` — **alto**

O regex principal usa `\p{Extended_Pictographic}` (`index.html:658`), que
**inclui** U+00A9 (`©`), U+00AE (`®`) e U+2122 (`™`). Remover emoji apaga,
portanto, avisos de copyright e marcas registradas do texto.

O regex de *fallback* (`:660`) é ainda mais amplo: `[\u2600-\u27BF]` cobre
toda a faixa de símbolosMiscellaneous e de dingbats, incluindo `✓` (U+2713),
`✗` (U+2717), `★`, `☆`, `♂`, `♀`, `⚙`, `✈` e `⛔` — símbolos que podem ter
significado em contexto técnico ou em checklist acadêmico.

**Mitigação:** lista de exceção explícita; remoção apenas de pictogramas
decorativos.

### 6.6 Aspas curvas perdem a distinção de citação literal — **médio**

Todos os tipos de aspas são convertidos para `"` e `'`. Em ABNT, a citação
literal exige aspas duplas e, em alguns manuais, tipografia diferenciada
para citação de citação. Perder a distinção de aspas impede a detecção
automática de **citação literal** — que é justamente o que o sistema precisa
proteger na Onda 3.

**Mitigação:** tratar aspas curvas como marca de citação literal e
**preservá-las** (o original as apaga).

### 6.7 Tabelas em ASCII/Unicode podem ser deformadas — **médio**

Os pseudo-gráficos de caixa são convertidos para `+`, `-`, `|`, preservando
*alguma* forma, mas a tabela passa a ter largura irregular e as células
alinhadas por espaços deixam de alinhar quando a fonte é proporcional. O
resultado é uma tabela que *parece* quebrada.

**Mitigação:** detectar tabelas (região de linhas com alinhamento consistente
de `|`/box-drawing) e tratá-las como **bloco atômico** (`TableData` no IR).

### 6.8 Outras observações

| Observação | Detalhe |
|---|---|
| Sem proteção de contexto | Nenhuma regra considera se o trecho é fórmula, citação ou referência |
| Sem estatísticas de perda | Apenas contagens; não informa **o que** foi removido |
| Sem reversibilidade | O texto original só existe no `<textarea>` de entrada |
| Sem idempotência testada | A limpeza de Markdown e o NFKC podem interferir entre si; o NFKC **depois** de um `*` ter sido removido muda o resultado |
| Regex sem `u` flag em alguns pontos | `countMatches` e algumas substituições usam regex sem a flag `u`, com comportamento divergente em caracteres astral |
| `emphHasCapture1` | Hack fragile que detecta, por inspeção de `source`, se a regex tem grupo de captura — sinal de fragilidade |

---

## 7. Tabela de decisões: o que aproveitar, o que refazer

| Componente do original | Decisão | Justificativa |
|---|---|---|
| Catálogo de transformações | **Reimplementar** (fonte de requisitos) | Útil como especificação; código sob GPL não é copiável |
| Arquitetura de UI (2 painéis + KPIs) | **Reaproveitar a ideia** | Boa UX; implementação própria |
| Debounce de 420 ms | **Reaproveitar a ideia** | Padrão de UX correto |
| `localStorage` apenas para idioma | **Reaproveitar** | Não é segredo; mantém o requisito de não guardar segredo |
| Remoção de emoji sem exceções | **Refazer** | §6.5 |
| NFKC como padrão | **Refazer** | §6.1 |
| Conversão de U+2212 | **Refazer** | §6.2 |
| Limpeza de Markdown sem contexto | **Refazer** | §6.3 |
| Conversão de setas | **Refazer** | §6.4 |
| Normalização de aspas | **Refazer** | §6.6 |
| Tabelas como texto | **Refazer** | §6.7 |
| Ausência de proteção de entidades | **Refazer** | Core do `ADR-0009` |
| Ausência de rastreabilidade por regra | **Refazer** | Core do `AGENTS.md` §3.6 |

---

## 8. Uso como oracle de teste (Onda 1)

Plano recomendado:

1. Congelar um conjunto de textos-fixture acadêmicos em
   `backend/tests/fixtures/` (versionados, anonimizados).
2. Executar o motor novo e o original sobre os mesmos textos.
3. **Classificar** cada diferença de forma explícita:
   - `esperada` — o novo motor é mais correto (ex.: preserva `10⁻⁶`);
   - `regressao` — o novo motor perdeu algo que o original mantinha;
   - `melhoria` — o original perdia algo irrelevante.
4. Aprovar cada fixture somente com a classificação de todas as diferencas
   registrada — o que transforma a comparação em **teste de regressão
   documental** versionado, como exige o `AGENTS.md` §6.

> O upstream **não** será adicionado como dependência nem como pacote de
> teste automatizado. As fixtures e as classificações são mantidas neste
> repositório.

---

## 9. Fontes

| Fonte | URL | Data de consulta |
|---|---|---|
| Repositório | <https://github.com/takumar-x/AI-Humanizer> | 2026-10-21 |
| `LICENSE` (local) | `LICENSE` do clone, 674 linhas | 2026-10-21 |
| `index.html` (local) | `index.html` do clone, 1080 linhas | 2026-10-21 |
| Texto da GPL-3.0 | <https://www.gnu.org/licenses/gpl-3.0.html> | 2026-10-21 |
| GNU:por que não LGPL | <https://www.gnu.org/licenses/why-not-lgpl.html> | 2026-10-21 |
| Unicode Standard (normalização) | <https://www.unicode.org/versions/Unicode16.0.0/> | 2026-10-21 |
| Unicode: Derived Property Values | <https://www.unicode.org/reports/tr44/> | 2026-10-21 |
