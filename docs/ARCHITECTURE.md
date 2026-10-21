# Arquitetura — Humaniza Acadêmico

> Documento canônico de arquitetura. Versão: Onda 0.
> Decisões que sustentam este documento estão em [`DECISIONS.md`](DECISIONS.md).

---

## 1. Visão geral

O sistema é um **pipeline de etapas independentes** sobre um documento
acadêmico. Cada etapa recebe uma revisão, devolve uma nova revisão e um
registro de transformações. Nenhuma etapa depende de LLM para produzir
resultado determinístico.

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Frontend   │   │    API       │   │   Serviços   │   │  Persistência│
│  React + TS  │◄─►│  FastAPI v1  │◄─►│  (domínio)   │◄─►│  SQLAlchemy  │
│  Vite/Tailwind│  │  /api/v1     │   │              │   │  SQLite/PG   │
└──────────────┘   └──────────────┘   └──────┬───────┘   └──────────────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    ▼                       ▼                       ▼
            ┌───────────────┐      ┌────────────────┐      ┌──────────────┐
            │  Providers    │      │  Templates     │      │  Exportador  │
            │  (LLM)        │      │  ABNT (YAML)   │      │  DOCX / PDF  │
            └───────────────┘      └────────────────┘      └──────────────┘
```

### 1.1 Camadas e regra de dependência

```
api  ──►  services  ──►  ir
 │           │           ▲
 │           ▼           │
 │        repositories   │
 │           │           │
 └────────► core  ────────┘

providers  ⇄  services/humanizer   (NÃO conversam com services/academic)
academic  ⇄  services/references   (NÃO conversam com providers)
```

Regras invioláveis (verificadas por revisão e por `ADR-0002`):

1. `services/academic/**` **nunca** importa `services/providers/**`.
2. `services/providers/**` **nunca** importa `services/academic/**`.
3. `services/normalizer/**` **nunca** importa `services/providers/**` — a
   normalização é garantidamente livre de LLM.
4. Nenhuma camada acima de `services/` (API) escreve regra de negócio; ela
   apenas orquestra serviços.
5. Todo serviço público recebe e devolve tipos do IR ou dos schemas.

---

## 2. Fluxo de dados

### 2.1 Diagrama do pipeline principal

```
   texto bruto (string)
          │
          ▼
   ┌─────────────┐
   │ IMPORT      │  cria AcademicDocument(original_text=...)  [imutável]
   └──────┬──────┘
          ▼
   ┌─────────────┐  regras puras e determinísticas
   │ NORMALIZE   │  (Unicode, invisíveis, espaços, Markdown, emojis)
   │             │  → NormalizationReport (contagens por regra)
   └──────┬──────┘
          ▼
   ┌─────────────┐  heurísticas + IR
   │ STRUCTURE   │  blocos, títulos, parágrafos, listas, tabelas
   └──────┬──────┘
          ▼
   ┌─────────────┐  números, datas, citações, DOI, fórmulas, pessoas
   │ PROTECT     │  → ProtectionCatalog + placeholders estáveis
   └──────┬──────┘
          ▼
   ┌─────────────┐  ◄── opcional, requer provedor + chave
   │ HUMANIZE    │  perfil autoral + intensidade (0..100) como orientação
   │             │  texto mascarado vai ao LLM; volta desmascarado
   └──────┬──────┘
          ▼
   ┌─────────────┐  compara entidades protegidas antes/depois
   │ VALIDATE    │  → ValidationReport (severidade por achado)
   │ (semântico) │
   └──────┬──────┘
          ▼
   ┌─────────────┐  diff por trecho, aceitar/rejeitar por sugestão
   │ REVIEW      │  (humano — bloqueia aprovação automática)
   └──────┬──────┘
          ▼
   ┌─────────────┐  template + perfil institucional
   │ TEMPLATE    │  → TemplateResolved (regras efetivas + conflitos)
   └──────┬──────┘
          ▼
   ┌─────────────┐  determinístico; LLM não participa
   │ FORMAT      │  → DOCX com estilos nativos do Word
   └──────┬──────┘
          ▼
   ┌─────────────┐  conformidade por regra, com fonte
   │ VALIDATE    │  → ComplianceReport
   │ (acadêmico) │
   └──────┬──────┘
          ▼
   ┌─────────────┐
   │ EXPORT      │  DOCX / PDF / TXT / Markdown
   └─────────────┘
```

### 2.2 Modelo de revisões

`AcademicDocument` mantém:

- `original_text` — **imutável** desde a criação;
- `revisions` — lista append-only de `DocumentRevision`;
- `current_revision_id` — ponteiro para a revisão vigente;
- `protection` — `ProtectionCatalog` da revisão vigente.

Toda etapa cria uma `DocumentRevision` com:

| Campo | Finalidade |
|---|---|
| `stage` | Etapa que produziu a revisão |
| `text` | Texto resultante |
| `blocks` | Estrutura de blocos (quando aplicável) |
| `transformations` | Registro por regra, com contagem e localização |
| `parent_id` | Revisão de origem |
| `metadata` | Tokens, custo, modelo, perfil, etc. |

> A imutabilidade é garantida por `model_config = ConfigDict(frozen=True)` em
> todos os modelos do IR. `with_revision()` devolve uma **cópia**; o objeto
> original nunca é mutado.

### 2.3 Origem e rastreabilidade

Todo `InlineSpan` e todo `Block` carregam `source_range: SourceRange`, com
offsets em **code points** Unicode (não bytes, não unidades UTF-16). Isso
garante que o mesmo texto produza os mesmos offsets em Python e em
TypeScript, o que é requisito para o diff lado a lado do frontend.

`SourceRange` é sempre relativo ao **original**, nunca à revisão corrente.
Assim, um alerta do validador semântico pode apontar exatamente o trecho do
documento do autor que originou a divergência.

---

## 3. Representação intermediária (`app/ir/`)

O IR é o **contrato central** do sistema. Quatro módulos:

### 3.1 `app/ir/spans.py` — trechos inline

`InlineSpan` é a unidade atômica de conteúdo inline:

```python
class InlineSpan(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    kind: SpanKind        # text | emphasis | strong | code_inline | code_block |
                          # math | equation | link | citation | footnote_ref |
                          # quote | preserved | field | line_break | tab
    text: str
    source_range: SourceRange | None
    attributes: dict[str, Any]
    protected_ids: tuple[str, ...]
```

Duas propriedades importantes:

- `is_lossless_target` — trechos que **nunca** podem ser reescritos
  automaticamente (código, matemática, equação, citação, placeholder, campo).
- A lista de spans é **plana**, não uma árvore. Isso permite fatiar e
  remontar o texto com offsets estáveis durante a fase de máscara, sem
  rebalancear uma árvore de rich text.

### 3.2 `app/ir/blocks.py` — blocos estruturais

`BlockKind` cobre o ciclo completo do documento acadêmico:

- **Pré-textuais**: `COVER`, `TITLE_PAGE`, `APPROVAL_PAGE`, `CATALOG_RECORD`,
  `ERRATA`, `DEDICATION`, `ACKNOWLEDGMENTS`, `EPIGRAPH`, `ABSTRACT_PT`,
  `ABSTRACT_EN`, `KEYWORDS`, `LIST_OF_ILLUSTRATIONS`, `LIST_OF_TABLES`,
  `LIST_OF_ABBREVIATIONS`, `LIST_OF_SYMBOLS`, `TABLE_OF_CONTENTS`.
- **Textuais**: `HEADING` (com `level`), `PARAGRAPH`, `QUOTE`, `QUOTE_LONG`,
  `LIST_ITEM`, `TABLE`, `FIGURE`, `CAPTION`, `SOURCE_NOTE`, `EQUATION`,
  `CODE_BLOCK`, `FOOTNOTE_TEXT`.
- **Pós-textuais**: `REFERENCES`, `REFERENCE_ITEM`, `GLOSSARY`, `APPENDIX`,
  `ANNEX`, `INDEX`.
- **Auxiliares**: `PAGE_BREAK`, `SECTION_BREAK`, `NOTE`, `EMPTY`.

`PAGE_BREAK_BLOCKS` marca os blocos que, por regra geral, iniciam em página
nova. A regra por template/instituição pode sobrescrever isso.

`TableData` preserva tabelas como unidade atômica (`rows` em ordem de
leitura), evitando que regras de texto processem células isoladamente.

### 3.3 `app/ir/protection.py` — catálogo de entidades protegidas

`ProtectedKind` enumera 17 categorias: `NUMBER`, `DATE`, `CITATION`,
`REFERENCE`, `DOI`, `URL`, `FORMULA`, `TERM_DEFINED`, `PERSON`,
`INSTITUTION`, `STATISTIC`, `TABLE_ID`, `FIGURE_ID`, `CODE`,
`QUOTE_LITERAL`, `UNIT`, `SPECIMEN`.

Cada entidade tem um `level` de proteção (`CRITICAL`, `HIGH`, `MEDIUM`,
`LOW`) e um `fingerprint` — hash do valor **normalizado**, usado para
comparar revisões.

A normalização do fingerprint usa a heurística:

| Entrada | Normalizada | Regra |
|---|---|---|
| `1.000` | `1000` | 3 dígitos após o separador → separador de milhar |
| `45,5%` | `45.5%` | demais separadores entre dígitos → decimal canônico |
| `−5` (U+2212) | `-5` | unifica sinais de menos |
| `1 234` | `1234` | remove espaços internos |

> O fingerprint é usado **apenas para comparação**. Ele nunca reescreve o
> valor exibido. A ambiguidade `1.000` (milhar em pt-BR vs. `1.0` em en-US)
> é documentada e aceita, dado que o produto opera em pt-BR.

Duas operações centralizam a detecção de perda de informação:

- `missing_fingerprints(other)` — entidades presentes no original e
  **ausentes** na revisão → sinaliza *omissão*.
- `changed_fingerprints(other)` — entidades cujo valor **mudou** → sinaliza
  *alteração*.

### 3.4 `app/ir/document.py` — documento e metadados

`DocumentMetadata` cobre o formulário de metadados exigido: instituição,
unidade acadêmica, curso/programa, autor, título, subtítulo, natureza,
objetivo acadêmico, orientador, coorientador, área de concentração, cidade,
ano, palavras-chave (pt/en) e idioma.

`DocumentMetadata.missing_required()` devolve a lista de campos obrigatórios
ausentes — base para a validação de completude antes da formatação.

`Transformation` é o registro unitário de uma alteração:

```python
class Transformation(BaseModel):
    stage: PipelineStage
    rule_id: str          # ex.: "norm.invisible.zwsp"
    description: str
    count: int
    source_range: SourceRange | None
    before: str
    after: str
    severity: str         # info | warning | critical
```

---

## 4. Estratégia de preservação de conteúdo

Esta é a seção mais crítica do sistema. A preservação é implementada em
**cinco camadas** independentes, para que a falha de uma não anule as demais.

### Camada 1 — Regra que não toca conteúdo protegido

Cada `NormalizationRule` declara `touches_protected_content: bool`. Regras
que podem alterar números, fórmulas ou citações **não podem** ser aplicadas
automaticamente. A regra é aplicada por faixa: o motor segmenta o texto em
trechos protegidos e livres, e aplica a regra apenas nos livres.

### Camada 2 — Máscara antes da LLM

Antes de qualquer chamada ao provedor:

1. o extrator identifica as entidades no IR;
2. cada entidade é substituída por um **placeholder estável** (`⟦P0042⟧`);
3. o texto mascarado é enviado ao LLM;
4. a resposta é desmascarada — e toda entidade que o LLM **não reproduziu**
   é restaurada, e toda entidade que o LLM **alterou** é revertida para o
   valor original, com o evento registrado.

O placeholder nunca é interpretado como texto a ser estilizado.

### Camada 3 — Validação semântica pós-revisão

`semantic_validator` compara o catálogo de entidades antes e depois:

- entidades perdidas → severidade `critical`, **bloqueia aprovação automática**;
- entidades alteradas → severidade `high`, exige aprovação explícita;
- citações literais divergentes → severidade `critical`;
- novos números introduzidos sem lastro no original → severidade `high`
  (possível invenção de resultado).

### Camada 4 — Estrutura determinística

Tabelas, equações, blocos de código e campos do Word são blocos atômicos no
IR. O formatador nunca os reconstrói a partir de texto corrido; ele os
transporta.

### Camada 5 — Regra ABNT parametrizada

Nenhuma regra de formatação ABNT é hard-coded. Cada regra vive no template
(YAML) com sua **fonte** (`norm`, `edition`, `section`, `url`, `consulted_at`,
`confidence`). O relatório de conformidade cita a fonte de cada regra.

### 4.1 Matriz de proteção por operação

| Operação | Números | Citações | Fórmulas | DOI/URL | Tabelas | Código |
|---|---|---|---|---|---|---|
| Normalização Unicode | preservado | preservado | preservado | preservado | preservado | preservado |
| Limpeza de Markdown | **fora de bloco** | preservado | preservado | preservado | preservado | **fora de bloco** |
| Remoção de emoji | preservado | preservado | preservado | preservado | preservado | preservado |
| Humanização por LLM | mascarado | mascarado | mascarado | mascarado | atômico | mascarado |
| Formatação ABNT | determinístico | determinístico | determinístico | determinístico | determinístico | determinístico |

---

## 5. Contratos principais

### 5.1 `LLMProvider` (`app/services/providers/base.py`)

```python
class LLMProvider(abc.ABC):
    provider_id: ProviderId
    requires_key: bool = True

    async def list_models(self) -> Sequence[ModelInfo]: ...
    async def check_credentials(self) -> CredentialCheck: ...
    async def generate(self, request: LLMRequest) -> LLMResponse: ...
    async def stream(self, request: LLMRequest) -> AsyncIterator[str]: ...
    async def cancel(self, request_id: str) -> bool: ...
    def estimate_cost(self, model, prompt_tokens, completion_tokens) -> float: ...
```

Invariantes:

- entrada/saída **independentes do fornecedor**;
- credenciais **nunca** em log, exceção ou resposta de API;
- todo erro é normalizado em `ProviderError` (com `code`, `retryable`,
  `retry_after_seconds`, `status_code`);
- custos são **estimados**, nunca cobrados.

`ProviderError.to_public_dict()` é a única forma de expor erro ao cliente —
garante que nenhum detalhe sensível vaze.

A Onda 2 implementa o contrato com HTTP direto via `httpx` (ver adendo do
`ADR-0004`), em cinco adaptadores (`openai_provider.py`,
`anthropic_provider.py`, `gemini_provider.py`, `ollama_provider.py`,
`openai_compat.py`) resolvidos pelo `registry.py`. A resiliência fica em
`resilience.py` (timeout, retry com backoff exponencial + jitter, respeito a
`Retry-After`), a estimativa de tokens/custo em `usage.py` e a resolução de
chaves em `credentials.py` (AES-GCM; a API expõe apenas `configured`/`last4`).

### 5.2 `NormalizationRule` (`app/services/normalizer/rules/base.py`)

```python
class NormalizationRule(abc.ABC):
    rule_id: str                  # "norm.invisible.zwsp" — chave estável
    description: str
    category: str
    configurable: bool
    enabled_by_default: bool
    touches_protected_content: bool

    def apply(self, text: str) -> RuleResult: ...
```

Toda regra é isolada, testável, ligável/desligável e medível. O motor
compõe as regras em pipeline determinístico e acumula as ocorrências em um
`NormalizationReport`.

### 5.2.1 Mapa de regras (`app/services/normalizer/rules/`)

O catálogo tem 29 regras, aplicadas em ordem fixa (`PIPELINE_ORDER`).
Cada regra declara `touches_protected_content` e `protected_kinds` — o motor
isola os trechos protegidos antes de aplicar a regra, de modo que nenhuma
transformação alcança números, fórmulas, citações, DOIs, URLs, tabelas ou
código.

| `rule_id` | Grupo | Padrão | Risco |
|---|---|---:|---|
| `norm.unicode.linebreak` | unicode | ligada | baixo |
| `norm.invisible.zwsp` | invisíveis | ligada | baixo |
| `norm.invisible.bidi` | invisíveis | ligada | médio (inverte exibição) |
| `norm.invisible.soft_hyphen` | invisíveis | ligada | baixo |
| `norm.invisible.variation` | invisíveis | ligada | baixo |
| `norm.control.strip` | invisíveis | ligada | baixo |
| `norm.ansi.strip` | invisíveis | ligada | baixo |
| `norm.unicode.nfkc` | unicode | **desligada** | **alto** (destrói `10⁻⁶`, `x²`) |
| `norm.unicode.nfc` | unicode | ligada | baixo |
| `norm.html.entities` | html | ligada | médio |
| `norm.pseudographics` | símbolos | ligada | médio (preserva setas e tabelas) |
| `norm.dash.normalize` | símbolos | ligada | alto (preserva U+2212) |
| `norm.quotes.ascii` | símbolos | ligada | médio (preserva citação literal) |
| `norm.ellipsis.ascii` | símbolos | ligada | baixo |
| `norm.bullet.normalize` | símbolos | ligada | baixo |
| `norm.markdown.divider` | markdown | ligada | baixo |
| `norm.markdown.heading` | markdown | ligada | baixo |
| `norm.markdown.heading_empty` | markdown | ligada | baixo |
| `norm.markdown.quote` | markdown | ligada | médio |
| `norm.markdown.bullet` | markdown | ligada | baixo |
| `norm.markdown.emphasis` | markdown | ligada | **alto** (protege subscritos) |
| `norm.markdown.code` | markdown | ligada | médio |
| `norm.markdown.escape` | markdown | ligada | baixo |
| `norm.emoji.remove` | emoji | ligada | alto (preserva `©`, `®`, `™`) |
| `norm.whitespace.nbsp` | espaços | ligada | baixo |
| `norm.punctuation.space_before` | espaços | ligada | baixo |
| `norm.whitespace.collapse` | espaços | ligada | baixo |
| `norm.whitespace.trailing` | espaços | ligada | baixo |
| `norm.whitespace.blank_lines` | espaços | ligada | baixo |

A ordem do pipeline importa: quebras de linha e invisíveis primeiro, NFKC
antes da limpeza de Markdown (para expor formas compostas), e os espaços por
último.

### 5.3 Padrão de revisão

```python
class HumanizerService:
    def __init__(self, provider: LLMProvider) -> None: ...

    async def humanize(
        self, text: str, *, profile: AuthorialProfile, intensity: Intensity, model: str
    ) -> ReviewResult: ...
```

`ReviewResult` carrega: texto revisado (com as entidades protegidas
restauradas ao original), análise, traços de estilo, o relatório de validação
semântica (`ValidationReport`) e o consumo estimado. O caller decide o que
fazer com os achados — a camada de humanização **não** aprova nada sozinha.

O ciclo é: extrair e **mascarar** as entidades protegidas (`⟦P0001⟧`), chamar
o provedor, **restaurar** os valores originais e **validar** os catálogos
antes/depois (`app/services/semantic_validator/`), implementando o portão de
aprovação do `ADR-0013`.

---

## 6. Módulo por módulo

| Módulo | Onda | Responsabilidade | Não faz |
|---|---|---|---|
| `ir/` | 0 | Modelo intermediário, proteção, revisões | Regras de negócio |
| `core/` | 0 | Config, logging, erros | Lógica de domínio |
| `services/normalizer/` | 1 | Limpeza de texto, sem LLM | Estrutura acadêmica |
| `services/providers/` | 2 | Adaptadores de LLM, retry, custo | Formatação |
| `services/humanizer/` | 3 | Perfil, intensidade, estilo, diff | Tocar layout |
| `services/semantic_validator/` | 3 | Comparação de entidades | Reescrever texto |
| `services/academic/` | 4 | Estrutura, numeração, estilos, paginação | Chamar LLM |
| `services/references/` | 5 | Citações, referências, NBR 6023 | Inventar metadados |
| `services/document_export/` | 6 | DOCX, PDF, TXT, Markdown | Decidir estilo |
| `api/v1/` | 0–7 | Rotas HTTP, validação de borda | Regra de negócio |
| `repositories/` | 0–8 | Persistência | Regras de negócio |

### 6.1 Padrão de módulo de serviço

Todo serviço segue a mesma forma:

```python
class NomeDoServico:
    def __init__(self, ...) -> None: ...

    async def executar(self, entrada: X) -> Resultado: ...
```

- Entrada e saída são **dataclasses/Pydantic** do IR ou dos schemas.
- I/O externa é `async`; CPU-bound (PDF, DOCX grande) vai para
  `asyncio.to_thread` ou subprocesso.
- Erros de domínio usam `HumanizaError` (subclasses com `code` e
  `status_code`).
- Nenhuma regra de negócio mora na camada de API.

---

## 7. Formatação ABNT e templates

### 7.1 Estrutura de template

```
templates/
├── abnt/<tipo>/<template>.yaml
├── institutions/<sigla>/<perfil>.yaml
└── schemas/template.schema.json
```

Um template declara:

```yaml
id: abnt.tcc.geral
version: 1.0.0
kind: tcc
extends: abnt.general
sources:
  - norm: "ABNT NBR 14724"
    edition: "2024"
    section: "5.1"
    url: "https://..."
    consulted_at: "2026-10-21"
    confidence: high
page:
  size: A4
  margins_cm: { top: 3, left: 3, right: 2, bottom: 2 }
  mirror: true          # margens distintas para anverso/verso
  numbering: { position: top_outside, start_at: first_textual }
typography:
  font: "Times New Roman"
  size_pt: 12
  line_spacing: 1.5
elements:
  - { id: cover, kind: cover, required: true }
  - { id: toc, kind: table_of_contents, required: true }
styles:
  heading1: { font_size_pt: 12, bold: true, spacing_before_pt: 12 }
```

### 7.2 Precedência

```
instituição  >  template do tipo de documento  >  norma geral ABNT
```

Conflitos são **registrados** no `TemplateResolved.conflicts`, nunca
resolvidos silenciosamente. Ver `ADR-0007`.

### 7.3 Fontes

Toda regra declara a norma, a edição, a seção, a URL e a data de consulta.
Normas ABNT são protegidas por direitos autorais: reproduzimos **estrutura e
regras parametrizadas**, nunca o texto integral. O estado de verificação das
normas está em [`standards/ABNT_NORMS_RESEARCH.md`](standards/ABNT_NORMS_RESEARCH.md).

---

## 8. Persistência

SQLAlchemy 2.0 com estilo `Mapped[]`/`mapped_column`, Alembic para migrações.
SQLite em desenvolvimento, PostgreSQL em produção.

Entidades previstas:

| Tabela | Conteúdo |
|---|---|
| `documents` | Documento, dono, texto original, revisão corrente |
| `revisions` | Histórico de revisões (append-only) |
| `transformations` | Registro por regra e localização |
| `provider_credentials` | Credenciais cifradas (AES-GCM), com `last4` |
| `author_profiles` | Perfis autorais derivados de textos do próprio usuário |
| `exports` | Metadados de exportações (caminho, hash, formato) |
| `validation_reports` | Relatórios de conformidade e de validação semântica |

> `original_text` é stored separadamente e **nunca** é atualizado.

### 8.1 Segredos

- Credenciais **nunca** são retornadas ao frontend. A API expõe apenas
  `configured: bool` e `last4: str`.
- A chave de criptografia (`encryption_key`) vive **fora** do banco, em
  variável de ambiente/segredo do ambiente de execução.
- Logs passam por `redact_secrets` (`app/core/logging.py`).

---

## 9. Frontend

React 18 + TypeScript + Vite + Tailwind. Páginas previstas (Onda 7):
Dashboard, Editor, Normalização, Humanização, Comparação, Templates ABNT,
Validador, Histórico, Perfis autorais, Configurações de LLM, Exportação.

Princípios:

- **Segredos nunca no `localStorage`/`sessionStorage`.** A chave do LLM é
  enviada ao backend por HTTPS e mantida apenas no backend.
- O editor exibe comparação lado a lado com diff por trecho, aceitação e
  rejeição por sugestão, e restauração do texto original.
- Cada chamada da API devolve também o **relatório da etapa** (contagens por
  regra, achados de validação, custo estimado, tokens).

---

## 10. Segurança

| Ameaça | Mitigação | Onda |
|---|---|---|
| Vazamento de chave em log | `redact_secrets` obrigatório | 0 |
| Chave devolvida ao cliente | API expõe só `configured`/`last4` | 2 |
| Segredo no `localStorage` | Segredos só no backend | 2 |
| Prompt injection via documento | Texto importado é **conteúdo**, delimitado e nunca interpretável como instrução | 2–3 |
| Upload malicioso | Limite de tamanho, magic bytes, nome sanitizado, sem path traversal | 8 |
| SSRF em consulta de DOI | Allowlist de hosts, opt-in, timeout | 5 |
| Path traversal em template | Templates lidos de diretório allowlisted, ID validado contra schema | 4 |
| Cross-tenant | `owner_id` obrigatório em toda consulta | 8 |
| Registro de segredo em exceção | `ProviderError` não inclui credencial | 2 |

---

## 11. Decisões técnicas de implementação

| Tema | Decisão | ADR |
|---|---|---|
| Modelo intermediário | IR próprio, `frozen=True`, spans planos | `ADR-0003` |
| Fornecedores | Adaptadores com `LLMProvider`; SDKs oficiais | `ADR-0004` |
| Formatação | Determinística; LLM fora do `academic/` | `ADR-0005` |
| Normalização | Sem LLM, regras puras e configuráveis | `ADR-0006` |
| Precedência de regras | instituição > template > norma | `ADR-0007` |
| Layout do repositório | Raiz do repo = raiz do projeto | `ADR-0008` |
| Proteção de dados | Catálogo + máscara + validação | `ADR-0009` |
| Toolchain Python | 3.12, `uv`, ruff, mypy strict, pytest | `ADR-0010` |
| Persistência | SQLAlchemy 2.0 + Alembic; SQLite dev / PG prod | `ADR-0011` |
| Exportação | DOCX nativo primeiro; PDF em processo isolado | `ADR-0012` |
| Aprovação | Bloqueio automático em perda de dado protegido | `ADR-0013` |

---

## 12. Limitações arquiteturais conhecidas

1. **Sem estado de multiusuário até a Onda 8.** Até lá, a API opera em modo
   local, sem autenticação. `owner_id` já existe no modelo para suportar o
   isolamento futuro.
2. **Renderização de PDF depende de ferramenta externa** (LibreOffice por
   padrão). Sem ela, apenas DOCX/TXT/Markdown são gerados, e a interface deve
   comunicar a limitação.
3. **Sumário automático é campo do Word**, não texto gerado. O DOCX exportado
   traz o campo `TOC` real; o sumário só aparece após a atualização de
   campos pelo Word (ou pelo LibreOffice).
4. **Detecção de proteção é heurística** (regex + contexto). Falsos
   negativos são possíveis; por isso a validação semântica sempre reporta
   também o que *não* conseguiu verificar.
5. **A ABNT não padroniza campos do Word.** A referência de sumário é a
   documentação da Microsoft; a conformidade é declarada sobre o *conteúdo*
   do sumário, não sobre o mecanismo de campo.
6. **Manuais institucionais desatualizados.** O manual UFMS disponível na
   biblioteca ainda referência a NBR 14724:2011 e a NBR 6023:2018, ambas
   superadas. Conflitos são registrados, não resolvidos por conta própria.
