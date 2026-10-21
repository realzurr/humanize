# ADR-0014 — Licença do projeto

- **Status**: **Proposta** (aguardando decisão do responsável)
- **Data**: 2026-10-21
- **Impacto**: Alto

## Contexto

O projeto **não** é GPL-3.0. A decisão de reimplementação *clean-room*
(`ADR-0001`) removes o copyleft do repositório de referência e não vincula o
produto a nenhuma licença copyleft.

Ainda assim, a licença definitiva do código, dos templates e da documentação
não foi definida, e essa escolha tem implicações práticas:

| Opção | Implicação |
|---|---|
| **Proprietaria / all rights reserved** | Sem redistribuição; permite instalação institucional fechada; impede contribuição externa |
| **MIT / BSD / Apache-2.0** | Permissiva; permite integração em produtos proprietários; facilita aceitação institucional |
| **AGPL-3.0** | Copyleft de rede; garante que modificações servidas permanecem públicas; exige publicação do código |
| **LGPL-3.0** | Copyleft de biblioteca; aplicável se o núcleo virar dependência distribuível |
| **CC BY-SA (documentação/templates)** | Permite uso dos templates com atribuição; obra derivada com compartilhamento da mesma licença |

## Estado atual

**Nenhum arquivo `LICENSE` foi adicionado ao repositório** e nenhuma
distribuição pública foi feita. A ausência de `LICENSE` é intencional até a
decisão: um arquivo com a licença errada é pior que nenhum.

Todas as dependências já declaradas em `backend/pyproject.toml` são de
licença permissiva ou copyleft fraco:

| Dependência | Licença |
|---|---|
| FastAPI, Starlette, Pydantic, Pydantic Settings | MIT |
| SQLAlchemy, Alembic | MIT |
| Uvicorn, HTTPX, HTTPX2 | BSD / BSD-3 |
| python-docx | MIT |
| docxtpl | MIT |
| PyMuPDF | AGPL-3.0 (!) — ver riscos R-38 e R-47 |
| PyYAML | MIT |
| bibtexparser | MIT |
| structlog | MIT / Apache-2.0 |
| cryptography | Apache-2.0 / BSD |
| ruff, mypy, pytest, pytest-asyncio, pytest-cov | MIT / BSD |

> ⚠️ **Riscos R-38 e R-47:** `PyMuPDF` é **AGPL-3.0**. Para um produto de
> licença proprietária, isso exige atenção: a AGPL alcança a obra que usa a
> biblioteca. Como o `PyMuPDF` é usado apenas para **inspeção e validação**
> (leitura de PDF, não oferta de serviço baseado em PDF), o risco é
> gerenciável, mas a decisão deve ser explicita. Alternativa permissiva:
> `pypdf` (BSD-3) para extração de texto e `pdfplumber` (MIT) para
> inspeção de estrutura. **Este ponto deve ser resolvido antes da Onda 6.**

## Decisão

Aguarda decisão do responsável pelo projeto. A escolha deve considerar:

1. O destino do produto (instituição pública, empresa, uso comercial).
2. A licença das dependências AGPL (`PyMuPDF`).
3. A licença dos templates ABNT: por serem parâmetros de regras e não texto
   de norma, podem ser compartilhados (CC BY-SA), mas isso precisa ser
   explícito.

## Consequências

- Até a decisão: nenhuma distribuição pública, nenhum `LICENSE` no
  repositório, e o status deste ADR permanece **Proposta**.
- A Onda 6 deve resolver a dependência AGPL antes de implementar o
  exportador PDF.

## Alternativas consideradas

| Alternativa | Motivo da rejeição (nesta rodada) |
|---|---|
| Assumir MIT silenciosamente | A escolha de licença é do responsável, não do agente |
| Assumir licença proprietária silenciosamente | Idem |
| Adotar GPL-3.0 como a referência | Confunde a licença da ferramenta de referência com a do produto; não há necessidade |
