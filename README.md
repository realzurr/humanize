# Humaniza Acadêmico

Plataforma web modular para **normalização textual**, **humanização semântica** e
**formatação acadêmica ABNT** de documentos acadêmicos em português brasileiro.

> **Estado do projeto:** Onda 2 (Integração Multi-LLM) concluída.
> A normalização textual determinística (sem LLM) e a camada de provedores de
> LLM (OpenAI, Anthropic, Gemini, Ollama e compatível) estão ativas. As ondas
> seguintes (humanização, templates, exportação) ainda não foram
> implementadas — ver [`docs/ROADMAP.md`](docs/ROADMAP.md).

---

## 1. O que o sistema faz (visão de produto)

O usuário insere ou importa um texto e percorre um pipeline **totalmente
etapado**, no qual qualquer etapa pode ser executada de forma independente:

```
DOCUMENTO ORIGINAL
    ↓  NORMALIZAÇÃO TEXTUAL              (sem LLM)
    ↓  IDENTIFICAÇÃO DA ESTRUTURA
    ↓  EXTRAÇÃO DE ELEMENTOS PROTEGIDOS
    ↓  SELEÇÃO DO PERFIL AUTORAL
    ↓  HUMANIZAÇÃO POR LLM               (etapa opcional)
    ↓  VALIDAÇÃO SEMÂNTICA
    ↓  COMPARAÇÃO E REVISÃO
    ↓  SELEÇÃO DO TEMPLATE ABNT
    ↓  FORMATAÇÃO DETERMINÍSTICA         (sem LLM)
    ↓  VALIDAÇÃO ACADÊMICA
    ↓  EXPORTAÇÃO DOCX/PDF
```

Princípios que atravessam todas as ondas:

| Princípio | Consequência prática |
|---|---|
| Normalização e formatação **nunca** usam LLM | Determinismo, custo zero, reprodutibilidade |
| O documento original é **imutável** | Toda etapa gera uma nova revisão rastreável |
| A LLM **nunca** decide layout | Margens, paginação e estilos são determinísticos |
| Informação verificável é **protegida** | Números, citações, fórmulas e DOI são mascarados antes da LLM |
| Conformidade é declarada **por regra** | Relatório por regra validada, com fonte e grau de confiança |
| Nada de inventar metadados | Referências e ficha catalográfica nunca são fictícias |

---

## 2. Repositório de referência e licenciamento

A análise detalhada do repositório de referência
[`takumar-x/AI-Humanizer`](https://github.com/takumar-x/AI-Humanizer) está em
[`docs/architecture/REFERENCE_REPO_ANALYSIS.md`](docs/architecture/REFERENCE_REPO_ANALYSIS.md).

**Resumo:** o repositório de referência é uma ferramenta client-side de arquivo
único (`index.html`, 1080 linhas) sob **GPL-3.0**. Ele normaliza texto
removendo caracteres invisíveis, emojis e pseudo-gráficos, além de limpeza de
Markdown e normalização Unicode.

**Decisão:** implementamos os requisitos funcionais **do zero** (*clean-room*),
sem copiar código do repositório. Isso evita o contágio copyleft da GPL-3.0
sobre o produto e mantém o projeto livre para escolha de licença própria.
Justificativa completa em [`ADR-0001`](docs/decisions/ADR-0001-clean-room-reimplementation.md).

> ⚠️ O repositório de referência **não é a fonte de verdade** para o
> comportamento do normalizador. A versão dele possui regressões graves para
> texto acadêmico (NFKC destruindo superíndices, setas químicas convertidas em
> `>`, remoção de `©`/`®`/`™`, subíndices com `_` comidos pelo limpador de
> Markdown). O catálogo completo está em
> [`docs/architecture/REFERENCE_REPO_ANALYSIS.md`](docs/architecture/REFERENCE_REPO_ANALYSIS.md#6-regressões-identificadas).

---

## 3. Estrutura do repositório

```
humaniza-academico/                 # raiz do repositório
├── backend/                        # API FastAPI (Python 3.12+)
│   ├── app/
│   │   ├── api/v1/                 # rotas HTTP
│   │   ├── core/                   # config, logging, erros de domínio
│   │   ├── ir/                     # ★ documento intermediário (contrato central)
│   │   ├── models/                 # modelos ORM (SQLAlchemy)
│   │   ├── repositories/           # acesso a dados
│   │   ├── schemas/                # schemas Pydantic de request/response
│   │   └── services/
│   │       ├── normalizer/         # Onda 1  (sem LLM)
│   │       ├── providers/          # Onda 2  (OpenAI/Anthropic/Gemini/Ollama)
│   │       ├── humanizer/          # Onda 3  (perfis, intensidade, estilo)
│   │       ├── semantic_validator/ # Onda 3  (proteção de dados)
│   │       ├── academic/           # Onda 4  (estrutura, estilos, numeração)
│   │       ├── references/         # Onda 5  (citações, referências, NBR 6023)
│   │       └── document_export/    # Onda 6  (DOCX, PDF)
│   ├── alembic/                    # migrações de banco
│   └── tests/                      # unit/ e integration/
├── frontend/                       # SPA React + TypeScript + Vite + Tailwind
│   └── src/{components,pages,services,hooks,types,styles}
├── templates/                      # templates de formatação (YAML/JSON)
│   ├── abnt/                       # general, articles, tcc, monographs, …
│   ├── institutions/               # ufms, ufgd
│   └── schemas/                    # JSON Schema dos templates
├── docs/
│   ├── ARCHITECTURE.md             # ★ arquitetura e fluxo de dados
│   ├── ROADMAP.md                  # ★ ondas, escopo e critérios de aceite
│   ├── DECISIONS.md                # ★ registro de decisões (ADRs)
│   ├── architecture/               # análises de referência, fluxo, riscos
│   ├── standards/                  # pesquisa das normas ABNT com fontes
│   ├── waves/                      # relatórios de onda
│   └── decisions/                  # ADRs individuais
├── scripts/
├── AGENTS.md                       # ★ regras permanentes de desenvolvimento
├── docker-compose.yml
└── .env.example
```

> **Desvio justificado da estrutura sugerida:** a especificação original
> mostra um diretório externo `humaniza-academico/`. Como este repositório já
> *é* o projeto, os diretórios foram criados na raiz, sem um nível extra de
> aninhamento. Ver [`ADR-0008`](docs/decisions/ADR-0008-repository-layout.md).

---

## 4. Início rápido (ambiente local)

Pré-requisitos: Python **3.12+**, Node.js **20+**, `uv` (recomendado).

### Backend

```bash
cd backend
uv venv --python 3.12
uv pip install -e ".[dev]"
uv run uvicorn app.main:app --reload --port 8000
```

- API: <http://127.0.0.1:8000>
- OpenAPI/Swagger: <http://127.0.0.1:8000/docs>
- Health check: `curl http://127.0.0.1:8000/api/v1/health`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

- Frontend: <http://127.0.0.1:5173>

### Verificação de qualidade (obrigatória antes de qualquer entrega)

```bash
cd backend
uv run ruff check .        # lint
uv run ruff format --check .  # formatação
uv run mypy                # tipagem estrita
uv run pytest              # testes
```

---

## 5. Configuração

Todas as chaves são lidas de variáveis de ambiente (arquivo `.env` local,
ignorado pelo git). O arquivo `.env.example` documenta todas as variáveis.

**Nenhuma chave de API tem valor padrão no código.** Um provedor sem chave é
reportado como indisponível — nunca como "funcionando". `Ollama` funciona
sem chave externa.

```bash
cp .env.example .env
```

---

## 6. Estado das ondas

| Onda | Escopo | Estado |
|---|---|---|
| 0 | Análise e preparação | ✅ concluída |
| 1 | Normalização textual (sem LLM) | ✅ concluída |
| 2 | Integração multi-LLM | ✅ concluída |
| 3 | Humanização semântica | ⛔ aguardando |
| 4 | Sistema de templates ABNT | ⛔ aguardando |
| 5 | Citações, referências e validador | ⛔ aguardando |
| 6 | Geração de documentos (DOCX/PDF) | ⛔ aguardando |
| 7 | Interface e experiência do usuário | ⛔ aguardando |
| 8 | Segurança, testes e estabilização | ⛔ aguardando |

Detalhamento, dependências e critérios de aceite em
[`docs/ROADMAP.md`](docs/ROADMAP.md).

---

## 7. Documentação

| Documento | Conteúdo |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Visão geral, camadas, fluxo de dados, IR, contratos |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Ondas, escopo, entregáveis, critérios de aceite, riscos |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Índice e resumo das decisões de arquitetura |
| [`docs/architecture/REFERENCE_REPO_ANALYSIS.md`](docs/architecture/REFERENCE_REPO_ANALYSIS.md) | Análise do repositório de referência e regressões |
| [`docs/standards/ABNT_NORMS_RESEARCH.md`](docs/standards/ABNT_NORMS_RESEARCH.md) | Normas ABNT verificadas, fontes e datas de consulta |
| [`docs/architecture/RISK_REGISTER.md`](docs/architecture/RISK_REGISTER.md) | Registro de riscos técnicos |
| [`docs/waves/onda-0.md`](docs/waves/onda-0.md) | Relatório da Onda 0 (análise e preparação) |
| [`docs/waves/onda-1.md`](docs/waves/onda-1.md) | Relatório da Onda 1 (normalização textual) |
| [`docs/waves/onda-2.md`](docs/waves/onda-2.md) | Relatório da Onda 2 (integração multi-LLM) |
| [`AGENTS.md`](AGENTS.md) | Regras permanentes de desenvolvimento (binding) |

---

## 8. Limitações e avisos

- O sistema **não** promete evasão de detectores de IA. O objetivo é qualidade
  de escrita e preservação rigorosa de significado.
- A conformidade ABNT é declarada **por regra validada**, com a respectiva
  fonte e o grau de confiabilidade. **Não** se presume conformidade integral.
- As normas ABNT são protegidas por direitos autorais: o sistema reproduz
  apenas a estrutura e as regras parametrizadas, acompanhadas de referência
  à fonte.
- Nenhum serviço é instalado ou modificado em servidores externos sem
  autorização expressa.
