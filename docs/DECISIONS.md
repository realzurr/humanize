# Registro de Decisões de Arquitetura

> Decisões que sustentam a arquitetura do Humaniza Acadêmico.
> Cada decisão tem um ADR individual em [`decisions/`](decisions/).
> Alterações em decisões aceitas exigem novo ADR (superseding) e registro
> aqui.

---

## Índice

| ADR | Título | Status | Data | Impacto |
|---|---|---|---|---|
| [ADR-0001](decisions/ADR-0001-clean-room-reimplementation.md) | Reimplementação *clean-room* do repositório de referência | ✅ Aceita | 2026-10-21 | Alto |
| [ADR-0002](decisions/ADR-0002-module-boundaries.md) | Limites de módulo e direção de dependência | ✅ Aceita | 2026-10-21 | Alto |
| [ADR-0003](decisions/ADR-0003-intermediate-representation.md) | Documento intermediário (IR) próprio como contrato central | ✅ Aceita | 2026-10-21 | Alto |
| [ADR-0004](decisions/ADR-0004-llm-provider-abstraction.md) | Abstração `LLMProvider` com adaptadores por fornecedor | ✅ Aceita | 2026-10-21 | Alto |
| [ADR-0005](decisions/ADR-0005-deterministic-formatting.md) | Formatação determinística; a LLM nunca define layout | ✅ Aceita | 2026-10-21 | Alto |
| [ADR-0006](decisions/ADR-0006-llm-free-normalization.md) | Normalização é livre de LLM e baseada em regras configuráveis | ✅ Aceita | 2026-10-21 | Alto |
| [ADR-0007](decisions/ADR-0007-template-precedence.md) | Precedência de regras: instituição > template > norma | ✅ Aceita | 2026-10-21 | Alto |
| [ADR-0008](decisions/ADR-0008-repository-layout.md) | Layout do repositório sem diretório externo de aninhamento | ✅ Aceita | 2026-10-21 | Médio |
| [ADR-0009](decisions/ADR-0009-protected-entity-catalog.md) | Catálogo de entidades protegidas + máscara antes da LLM | ✅ Aceita | 2026-10-21 | Alto |
| [ADR-0010](decisions/ADR-0010-python-toolchain.md) | Toolchain Python 3.12 com `uv`, ruff, mypy estrito, pytest | ✅ Aceita | 2026-10-21 | Médio |
| [ADR-0011](decisions/ADR-0011-persistence-stack.md) | SQLAlchemy 2.0 + Alembic; SQLite em dev, PostgreSQL em prod | ✅ Aceita | 2026-10-21 | Médio |
| [ADR-0012](decisions/ADR-0012-document-export.md) | Exportação DOCX nativa primeiro; PDF em processo isolado | ✅ Aceita | 2026-10-21 | Alto |
| [ADR-0013](decisions/ADR-0013-human-approval-gate.md) | Bloqueio de aprovação automática em perda de dado protegido | ✅ Aceita | 2026-10-21 | Alto |
| [ADR-0014](decisions/ADR-0014-project-license.md) | Licença MIT, autoria (`realzurr`) e créditos à referência | ✅ Aceita | 2026-10-21 | Alto |
| [ADR-0015](decisions/ADR-0015-abnt-sources-and-conformity.md) | Conformidade declarada por regra, com fonte e confiança | ✅ Aceita | 2026-10-21 | Alto |
| [ADR-0016](decisions/ADR-0016-pymupdf-optional-dependency.md) | `pymupdf` como dependência opcional (licenciamento AGPL) | ✅ Aceita | 2026-10-22 | Médio |
| [ADR-0017](decisions/ADR-0017-security-hardening-post-onda8.md) | Endurecimento de segurança pós-Onda 8 (Argon2id, rotação, rate limit, retenção) | ✅ Aceita (itens 3 e 4 ⛔ substituídos pelo ADR-0018) | 2026-10-22 | Médio |
| [ADR-0018](decisions/ADR-0018-revocation-redis-key-indirection.md) | Revogação persistida, rate limit Redis e indireção de chaves de LLM | ✅ Aceita | 2026-10-22 | Médio |
| [ADR-0019](decisions/ADR-0019-key-files-and-logout-all.md) | Chaves de LLM em arquivo e encerramento de todas as sessões | ✅ Aceita | 2026-10-22 | Baixo |

---

## Resumos

### ADR-0001 — Reimplementação *clean-room* ✅

O repositório de referência [`takumar-x/AI-Humanizer`](https://github.com/takumar-x/AI-Humanizer)
é GPL-3.0. Copiar, adaptar ou incorporar seu código tornaria o produto uma
obra derivada, com obrigação de licença GPL-3.0. Optamos por reimplementar os
requisitos funcionais do zero, **sem copiar código**, o que mantém a liberdade
de escolha de licença e evita dependência de um projeto de 3 estrelas, 9
commits e arquivo único. A análise detalhada, incluindo as regressões
acadêmicas do original, está em
[`architecture/REFERENCE_REPO_ANALYSIS.md`](architecture/REFERENCE_REPO_ANALYSIS.md).

### ADR-0002 — Limites de módulo ✅

`api → services → ir`; `core` transversal; `repositories` só em `api`/`services`.
Proibições explícitas: `academic` ⇄ `providers` nunca se conhecem;
`normalizer` nunca importa `providers`; nenhuma formatação de layout existe
fora de `services/academic` e `templates/`.

### ADR-0003 — Documento intermediário (IR) ✅

`app/ir/` define `InlineSpan`, `Block`, `ProtectionCatalog` e
`AcademicDocument`. Modelos `frozen=True`, `source_range` sempre relativo ao
original, spans planos (não árvore) para facilitar a fase de máscara. Nenhuma
etapa opera sobre texto solto.

### ADR-0004 — Abstração `LLMProvider` ✅

Um único contrato (`generate`, `stream`, `list_models`,
`check_credentials`, `cancel`, `estimate_cost`) e um `ProviderError`
normalizado. Adaptadores: OpenAI, Anthropic, Gemini, Ollama e
"openai-compatible" por configuração. Custos são estimados, nunca cobrados.

### ADR-0005 — Formatação determinística ✅

Margens, paginação, numeração, estilos e quebras de seção vêm **sempre** de
template. A LLM participa apenas do texto; qualquer tentativa de influence
layout é ignorada e registrada.

### ADR-0006 — Normalização livre de LLM ✅

O motor de normalização é uma cadeia de regras puras, cada uma com
`rule_id` estável, configurável e testável. As regras não tocam trechos
protegidos.

### ADR-0007 — Precedência de regras ✅

`instituição > template do tipo de documento > norma geral ABNT`. Conflitos
são registrados em `TemplateResolved.conflicts` e exibidos ao usuário, nunca
resolvidos silenciosamente.

### ADR-0008 — Layout do repositório ✅

A especificação original mostra um diretório externo `humaniza-academico/`.
Como o repositório já **é** o projeto, o conteúdo foi criado na raiz, sem
nível extra de aninhamento. Todos os demais diretórios seguem a
especificação.

### ADR-0009 — Catálogo de entidades protegidas ✅

Antes de qualquer chamada de LLM, números, datas, citações, DOI, URLs,
fórmulas, nomes, estatísticas, identificadores de tabela/figura, código e
citações literais são extraídos para um `ProtectionCatalog` e substituídos
por placeholders estáveis. A resposta é desmascarada e comparada com o
catálogo original.

### ADR-0010 — Toolchain Python ✅

Python 3.12 (via `uv`), `ruff` (lint + format, line-length 100), `mypy`
modo `strict`, `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`).
Instalação e verificação verificadas na Onda 0: 21 testes verdes, ruff e mypy
sem erros.

### ADR-0011 — Pilha de persistência ✅

SQLAlchemy 2.0 (`Mapped[]`/`mapped_column`) + Alembic. SQLite em
desenvolvimento, PostgreSQL em produção. `original_text` é armazenado
separadamente e nunca é atualizado. Migrações por Alembic — nunca
`create_all` em produção.

### ADR-0012 — Exportação de documentos ✅

DOCX com estilos nativos do Word, campos `TOC`/`PAGE`/`SEQ` reais e
referências cruzadas. PDF é renderizado a partir do DOCX por processo
isolado (LibreOffice), fora do event loop, com comparador DOCX↔PDF e
documentação de limitações. Sem renderizador disponível, a limitação é
declarada e apenas DOCX/TXT/Markdown são gerados.

### ADR-0013 — Bloqueio de aprovação automática ✅

Se a validação semântica detectar perda de entidade protegida de severidade
`CRITICAL`, o sistema **impede** a aprovação automática e exige revisão
humana explícita, com destaque da divergência.

### ADR-0014 — Licença do projeto, autoria e créditos ✅

O projeto é de autoria de **Renato Lemes Peixoto (`realzurr`)** e é distribuído
sob a **MIT License** (arquivo `LICENSE` na raiz), com atribuição explícita de
créditos conceituais ao repositório de referência
[`takumar-x/AI-Humanizer`](https://github.com/takumar-x/AI-Humanizer) (de
`takumar-x` / Mikhail Medvedev) pela inspiração inicial da etapa de
normalização textual.

### ADR-0015 — Fontes ABNT e declaração de conformidade ✅

Toda regra de formatação declara norma, edição, seção, URL, data de consulta
e grau de confiabilidade. A conformidade é declarada **por regra validada**.
Nenhuma conformidade integral é presumida. Normas protegidas por direitos
autorais não são reproduzidas na íntegra — apenas estrutura e regras
parametrizadas.

### ADR-0017 — Endurecimento de segurança pós-Onda 8 ✅

Argon2id (via `cryptography` ≥ 44) com *rehash* no login; rotação de chaves
por `PREVIOUS_*_KEYS` (CSV ou JSON); revogação de tokens em memória por
processo (limitação declarada); rate limit `memory`/`sqlite` — `redis` removido
da configuração até haver cliente e operação atômica; IP do cliente pela
entrada `-TRUSTED_PROXY_HOPS` do `X-Forwarded-For`; retenção apaga linha e
arquivo de exportação; inspetor nativo de PDF não declara margens.

### ADR-0018 — Revogação persistida, Redis e cofre de chaves ✅

Revogação de tokens no banco (`REVOCATION_BACKEND=database`, migração `0003`),
compartilhada entre workers e persistente. Rate limit `redis` com script Lua
atômico e relógio do servidor, `redis` como extra opcional. Chaves de LLM via
`<PROVEDOR>_API_KEY_ENV_NAME`, com nomes reservados bloqueados. Teste estático
dos cabeçalhos do Nginx.

### ADR-0019 — Chaves em arquivo e `logout-all` ✅

`<PROVEDOR>_API_KEY_FILE` (caminho absoluto, ≤ 4 KiB, lido a cada uso) como
última fonte de ambiente. `POST /auth/logout-all` revoga apenas os tokens do
próprio usuário; revogação de terceiros aguarda um papel administrativo.

---

## Convenção

- **Status**: `🟡 Proposta` · `✅ Aceita` · `⛔ Substituída` · `📝 Rascunho`.
- **Data**: formato ISO `YYYY-MM-DD`.
- Um ADR aceito não é editado: ele é **substituído** por um novo ADR, que
  referência o anterior na seção *Supersedes*.
- Decisões com impacto estrutural (camadas, IR, licença, segurança) exigem
  revisão humana explícita antes da implementação.
