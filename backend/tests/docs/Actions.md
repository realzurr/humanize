# Plano de Ação — Estratégia e Auditoria da Suíte de Testes (Humaniza Acadêmico)

> **Fase A — Análise, Auditoria de Qualidade e Plano de Ação (QA Strategy Planner)**
> - **Data da auditoria**: 2026-10-22
> - **Escopo de escrita permitido**: exclusivamente `backend/tests/` (demais diretórios tratados como *read-only*)
> - **Referências normativas de qualidade**: ISO/IEC 25010, ISO/IEC/IEEE 29119, ISTQB, Pirâmide de Testes, Princípios FIRST, Risk-Based Testing.

---

## 1. Resumo Executivo

- **O que é o projeto**: **Humaniza Acadêmico** é uma plataforma full-stack (FastAPI + React/TypeScript) para normalização textual determinística (sem LLM), humanização semântica assistida por múltiplos provedores de LLM com preservação de entidades científicas (máscara + validação semântica + portão de aprovação), estruturação e validação acadêmica segundo normas ABNT vigentes (NBR 14724:2024, NBR 6023:2025, NBR 10520:2023, NBR 6024:2012, etc.) e exportação nativa para DOCX, PDF, TXT e Markdown.
- **Arquitetura identificada**: Monólito modular em camadas estritas (`api → services → ir`, com `repositories` e `core` transversais), orientado por uma Representação Intermediária imutável (`app/ir/`, `frozen=True`). Isolamento arquitetural entre provedores de LLM (`app/services/providers/`) e formatação acadêmica (`app/services/academic/`).
- **Estado atual dos testes**:
  - **Backend**: 466 testes automatizados (`pytest`), todos passando (`22.01s`), cobertura de linhas global de **96%** (`5740` statements, `256` ausentes), `ruff check`, `ruff format --check` e `mypy --strict` (114 arquivos) sem erros. Organização atual em `tests/unit/` (35 arquivos), `tests/integration/` (11 arquivos) e `tests/regression/` (1 arquivo + 3 fixtures).
  - **Frontend**: 14 testes unitários em 4 arquivos (`vitest` + Testing Library) e 1 teste E2E (`playwright` em `frontend/tests/e2e/fluxo.spec.ts` com API mockada), `eslint` sem avisos.
- **Principais riscos e achados críticos**:
  Apesar da alta cobertura percentual (96%), a auditoria baseada em risco revelou **7 achados técnicos/bugs reais no código da aplicação** e **lacunas importantes na suíte de testes**, incluindo:
  1. **Vazamento cross-tenant de credenciais em memória** (`CredentialResolver._session` global sem `owner_id`) e **desconexão entre `PersistentCredentialStore` e `ProviderRegistry.build()`** (credenciais salvas no banco nunca são lidas para instanciar provedores de LLM).
  2. **Ausência de autenticação/isolamento por `owner_id`** nas rotas `/api/v1/exports`, `/api/v1/uploads` e `/api/v1/humanize`, além da tabela `exports` e `revisions` nunca serem gravadas pelos endpoints da API.
  3. **Bypass de Rate Limiting** via falsificação do cabeçalho `X-Forwarded-For`.
  4. **Ausência de camada de testes de componente (`tests/component/`)**, ausência de testes de contrato/concorrência/idempotência e testes de mutação/fronteira para cenários adversariais.
- **Estratégia recomendada**:
  Manter os testes existentes intactos e expandir a suíte dentro de `backend/tests/` seguindo a Pirâmide de Testes orientada a risco: criar testes que **reproduzam e documentem formalmente os bugs/vulnerabilidades encontrados** (sem alterar o código de produção nem enfraquecer asserções), adicionar testes de componente para pipelines integrados em memória, testes de segurança/isolamento multi-tenant em todas as rotas e testes de robustez/fronteira.

---

## 2. Tecnologias Identificadas

| Camada | Tecnologia / Biblioteca | Versão / Configuração (Evidência) |
|---|---|---|
| Linguagem (Backend) | Python | `>=3.12` (`backend/pyproject.toml`, `.venv` em Python 3.12.14) |
| Framework Web (Backend) | FastAPI + Uvicorn | `fastapi>=0.115`, `uvicorn[standard]>=0.32` (`app/main.py`) |
| Validação e Configuração | Pydantic v2 + Pydantic Settings | `pydantic>=2.9`, `pydantic-settings>=2.6` (`app/core/config.py`) |
| Banco de Dados e ORM | SQLAlchemy 2.0 + Alembic | `sqlalchemy>=2.0.36` (`Mapped[]`/`mapped_column`), `alembic>=1.14`, SQLite local / PostgreSQL prod |
| Criptografia e Segurança | `cryptography` + `hmac`/`hashlib`/`secrets` | AES-GCM (`SecretCipher`), PBKDF2-SHA256 600k iterações, HMAC-SHA256 (`app/core/security.py`) |
| Cliente HTTP e Resiliência | `httpx` + `tenacity` | `httpx>=0.27`, `tenacity>=9.0` (`app/services/providers/transport.py`, `resilience.py`) |
| Processamento Documental | `python-docx`, `docxtpl`, `pymupdf`, `pyyaml`, `bibtexparser` | Geração OpenXML nativa, inspeção de PDF, templates YAML, parser BibTeX |
| Logging | `structlog` | JSON/Console com processador obrigatório `redact_secrets` (`app/core/logging.py`) |
| Qualidade e Testes (Backend) | `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`, `mypy` | `asyncio_mode = "auto"`, `filterwarnings = ["error"]`, `mypy --strict` |
| Frontend | React 18 + TypeScript 5.7 + Vite 6 + Tailwind CSS 3.4 | SPA com 11 páginas (`frontend/package.json`, `frontend/src/App.tsx`) |
| Qualidade e Testes (Frontend) | Vitest 3.2 + Testing Library + Playwright 1.61 + ESLint 9 | `frontend/tests/unit/` (4 arquivos) e `frontend/tests/e2e/fluxo.spec.ts` |

---

## 3. Arquitetura Identificada

### 3.1 Módulos e Camadas (`backend/app/`)
1. **Representação Intermediária (`app/ir/`)**:
   - `spans.py` (`InlineSpan`, `SpanKind`, `SourceRange`), `blocks.py` (`Block`, `BlockKind`, `TableData`), `protection.py` (`ProtectedEntity`, `ProtectionCatalog`, `ProtectedKind`, `ProtectionLevel`, `normalize_fingerprint`), `document.py` (`AcademicDocument`, `DocumentMetadata`, `DocumentRevision`, `Transformation`). Todos `frozen=True`.
2. **Núcleo Transversal (`app/core/`)**:
   - `config.py` (`Settings`), `database.py` (`Base`, `make_engine`, `make_session_factory`, `get_session`), `errors.py` (`HumanizaError` e 10 subclasses mapeadas para HTTP 400/401/403/404/409/413/422/429/500/503), `logging.py` (`redact_secrets`), `ratelimit.py` (`SlidingWindowLimiter`, `client_ip`), `security.py` (`hash_password`, `verify_password`, `TokenService`).
3. **Modelos ORM e Repositórios (`app/models/`, `app/repositories/`)**:
   - Modelos: `User` (`users`), `ProviderCredential` (`provider_credentials`), `Document` (`documents`), `DocumentRevision` (`revisions`), `Export` (`exports`).
   - Repositórios: `UserRepository`, `CredentialRepository`, `DocumentRepository` (nota: não há repositório para `Export` nem para `DocumentRevision`).
4. **Serviços de Domínio (`app/services/`)**:
   - `normalizer/`: pipeline determinístico sem LLM com 29 regras (`rules/`), segmentação de spans protegidos (`protect.py`), perfis (`profile.py`) e estatísticas (`stats.py`).
   - `providers/`: contrato `LLMProvider` (`base.py`), 5 adaptadores HTTP (`openai_provider.py`, `anthropic_provider.py`, `gemini_provider.py`, `ollama_provider.py`, `openai_compat.py`), catálogo (`catalog.py`), resolução de credenciais em memória (`credentials.py`) e em banco (`persistent_credentials.py`), resiliência (`resilience.py`), transporte (`transport.py`) e custo/tokens (`usage.py`).
   - `humanizer/`: análise heurística (`analysis.py`), 7 perfis (`profiles.py`), 5 níveis de intensidade (`intensity.py`), extração de traços de estilo (`style_features.py`) e orquestrador (`engine.py`).
   - `semantic_validator/`: extrator (`extractor.py`), máscara `⟦P0001⟧` (`masker.py`) e validador pós-LLM (`validator.py`).
   - `academic/`: registro e herança de templates YAML (`templates.py`, `template_model.py`), estrutura (`structure.py`), numeração NBR 6024 (`numbering.py`), paginação anverso/verso (`pagination.py`), seções (`sections.py`), estilos (`styles.py`) e metadados (`metadata.py`).
   - `references/`: parser de referências (`parser.py`), parser de citações NBR 10520:2023 (`citation_parser.py`), associação citação↔referência (`matcher.py`), formatação NBR 6023:2025 (`nbr6023.py`), importadores BibTeX (`bibtex.py`) e CSL-JSON (`csl_json.py`), resolvedor opt-in de DOI Crossref (`doi.py`) e validador (`validator.py`).
   - `document_export/`: construtor OpenXML nativo e inspetor XML (`docx_builder.py`), campos dinâmicos Word `TOC`/`PAGE`/`NUMPAGES`/`SEQ`/`STYLEREF`/`REF` (`fields.py`), renderizador PDF isolado via LibreOffice e comparador DOCX↔PDF via PyMuPDF (`pdf_builder.py`), exportadores TXT/Markdown, preview e `ExportHistoryStore` (`writer.py`).
   - `ingestion/`: delimitadores contra prompt injection (`guard.py`) e validação/extração de uploads (`upload.py`).
5. **Camada de Borda HTTP (`app/api/v1/`, `app/schemas/`)**:
   - 10 módulos de rota sob `/api/v1`: `health`, `auth`, `uploads`, `documents`, `normalize`, `providers`, `humanize`, `templates`, `academic`, `exports`.

### 3.2 Fluxo Principal de Dados
`Entrada/Upload → Validação Pydantic/Magic Bytes → Normalização Determinística (Proteção de Spans) → Extração de Catálogo + Máscara (⟦Pxxxx⟧) + Envoltório Anti-Injection → Chamada Assíncrona ao LLMProvider → Desmascaramento + Remoção de Envoltório → Validação Semântica (Portão ADR-0013) → Resolução de Template ABNT/Institucional → Validação de Citações/Referências → Construção DOCX/PDF/TXT/MD → Persistência/Histórico → Resposta HTTP`

---

## 4. Mapa de Funcionalidades (Features Identificadas)

| ID | Funcionalidade | Módulo / Endpoint | Criticidade | Dependências | Testes Necessários |
|---|---|---|---|---|---|
| F-01 | Saúde e Prontidão (`/health`, `/health/readiness`) | `app/api/v1/health.py` | Baixa | `Settings`, `templates_dir`, Banco | Unitário + Integração (incluindo estado `degraded` quando `templates_dir` ausente) |
| F-02 | Registro, Login e Identidade (`/auth/register`, `/auth/token`, `/auth/me`) | `app/api/v1/auth.py`, `app/core/security.py`, `app/repositories/users.py` | **Crítica** | SQLite/PG (`users`), `TokenService`, `SlidingWindowLimiter` | Unitário (hash, expiração, adulteração, usuário inativo) + Integração (401, 409, 422, 429) |
| F-03 | Upload Seguro e Extração de Texto (`/uploads`) | `app/api/v1/uploads.py`, `app/services/ingestion/upload.py` | **Alta** | `python-docx`, Sistema de arquivos (`storage_dir`) | Unitário + Integração (magic bytes, NUL byte, UTF-8 inválido, DOCX corrompido, path traversal, limite 413, autenticação) |
| F-04 | Gestão e Retenção de Documentos (`/documents`, `/documents/prune`) | `app/api/v1/documents.py`, `app/repositories/documents.py` | **Alta** | SQLite/PG (`documents`, `revisions`), `get_current_user` | Unitário + Integração (CRUD, isolamento cross-tenant, cascade delete de revisões, `prune_expired` real via HTTP) |
| F-05 | Normalização Textual Determinística (`/normalize`, `/normalize/perfis`) | `app/api/v1/normalize.py`, `app/services/normalizer/` | **Crítica** | 29 regras (`rules/`), `protect.py`, `ProtectionCatalog` | Unitário (29 regras, idempotência, ordem do pipeline) + Componente + Regressão Científica (NFKC, fórmulas, unidades, tabelas, código) |
| F-06 | Catálogo de Provedores e Gestão de Credenciais (`/providers/**`) | `app/api/v1/providers.py`, `app/services/providers/` | **Crítica** | `CredentialResolver`, `PersistentCredentialStore`, `SecretCipher`, `ProviderRegistry` | Unitário + Componente + Integração (isolamento por `owner_id`, ciclo banco↔registro, redaction em logs, resiliência HTTP) |
| F-07 | Humanização Semântica e Portão de Aprovação (`/humanize`) | `app/api/v1/humanize.py`, `app/services/humanizer/`, `app/services/semantic_validator/` | **Crítica** | `LLMProvider`, `masker.py`, `validator.py`, `guard.py` | Unitário + Componente + Integração (7 perfis, 5 intensidades, omissão/alteração/invenção de números, prompt injection, rate limit) |
| F-08 | Resolução de Templates ABNT e Conflitos Institucionais (`/templates/**`) | `app/api/v1/templates.py`, `app/services/academic/` | **Alta** | `templates/` (YAML), `TemplateRegistry`, `numbering`, `pagination` | Unitário + Componente + Integração (herança `extends`, precedência `instituição > template > norma`, registro de conflitos UFMS/UFGD) |
| F-09 | Validação Acadêmica de Citações, Referências e DOI (`/academic/validate`) | `app/api/v1/academic.py`, `app/services/references/` | **Alta** | `parser`, `citation_parser`, `matcher`, `nbr6023`, `doi`, `bibtex`, `csl_json` | Unitário + Componente + Integração (citação órfã, referência não citada, duplicata, NBR 10520:2023, NBR 6023:2025, Crossref opt-in mockado) |
| F-10 | Exportação Documental DOCX/PDF/TXT/MD e Histórico (`/exports/**`) | `app/api/v1/exports.py`, `app/services/document_export/` | **Crítica** | `docx_builder`, `fields`, `pdf_builder`, `writer`, LibreOffice/PyMuPDF | Unitário + Componente + Integração (campos Word `TOC`/`PAGE`, ficha catalográfica reservada, fallback sem LibreOffice, download binário, retenção) |

---

## 5. Fluxos Críticos e Classificação de Risco

| ID | Fluxo | Risco Principal | Impacto | Prioridade |
|---|---|---|---|---|
| FC-01 | Preservação de entidades científicas na Normalização (`10⁻⁶`, `x²`, `CO₂`, `U+2212`, `→`, citações, DOI, tabelas) | Corrupção silenciosa de dados científicos por regras Unicode/Markdown/Emoji | **Crítico** | **P1 (Crítica)** |
| FC-02 | Ciclo de Máscara → LLM → Desmascaramento → Validação Semântica → Bloqueio (`ADR-0013`) | Omissão, alteração ou invenção de resultados estatísticos/numéricos pela LLM sem bloqueio | **Crítico** | **P1 (Crítica)** |
| FC-03 | Armazenamento, Criptografia (AES-GCM), Resolução e Isolamento Multi-Usuário de Chaves de API | Vazamento de chave de API entre usuários (cross-tenant), em logs ou falha ao usar chave persistida | **Crítico** | **P1 (Crítica)** |
| FC-04 | Autenticação, Autorização e Isolamento por `owner_id` em Documentos, Uploads, Exportações e Perfis Autorais | Acesso não autorizado ou sobrescrita/leitura de documentos e arquivos de outros usuários | **Crítico** | **P1 (Crítica)** |
| FC-05 | Geração de DOCX Nativo com Estilos Reais, Campos `TOC`/`PAGE` e Reserva de Ficha Catalográfica | Documento inválido no Word, simulação visual com espaços/tabs ou ficha catalográfica fictícia | **Alto** | **P2 (Alta)** |
| FC-06 | Resolução de Precedência de Templates (`instituição > template > norma`) e Declaração de Conflitos | Sobrescrita silenciosa de regra ABNT por manual institucional desatualizado (ex.: UFMS NBR 14724:2011) | **Alto** | **P2 (Alta)** |
| FC-07 | Validação de Citações/Referências (NBR 10520:2023 / NBR 6023:2025) e Proposta Opt-in via DOI | Invenção de metadados bibliográficos ou aplicação automática sem aprovação humana | **Alto** | **P2 (Alta)** |
| FC-08 | Resiliência de Provedores de LLM (Timeout, Retry Exponencial, `Retry-After`, Rate Limit, Cancelamento) | Travamento de workers, cascata de falhas ou cobrança indevida em provedores externos | **Médio** | **P3 (Média)** |

---

## 6. Estratégia da Pirâmide de Testes

```text
            Integração (API + DB + FS)
                   /\
                  /  \
                 /____\
         Componente (Pipelines/Módulos)
               /        \
              /__________\
        Unitário (Regras/Domínio/IR)
             /            \
            /______________\
```

### 6.1 Testes Unitários (Base — Maioria da Suíte)
- **Escopo**: Funções puras, modelos do IR (`app/ir/`), cada uma das 29 regras de normalização isoladamente, heurísticas de detecção de spans protegidos (`protect.py`), cálculo de fingerprints (`normalize_fingerprint`), primitivas criptográficas (`SecretCipher`, `hash_password`, `TokenService`), `SlidingWindowLimiter`, parsers de citações/referências/BibTeX/CSL-JSON, numeração progressiva NBR 6024 e cálculos de paginação/margens.
- **Critérios**: Execução em milissegundos, zero I/O de rede ou disco, determinismo estrito (Princípios FIRST).

### 6.2 Testes de Componente (Camada Intermediária — Atualmente Ausente na Estrutura)
- **Escopo**: Módulos completos operando com suas dependências internas reais, mockando apenas fronteiras externas (rede/subprocesso):
  1. **Pipeline de Normalização + Catálogo de Proteção**: `NormalizationEngine` + `build_default_rules()` + `protect.py` + `stats.py` garantindo idempotência (`engine.run(engine.run(x).text).text == engine.run(x).text`) e preservação de offsets.
  2. **Pipeline de Humanização + Validador Semântico + Guard**: `HumanizerService` + `extract` + `mask` + `unmask` + `validate` + `guard` com `FakeLLMProvider` adversarial (que remove placeholders, altera números, injeta novos números ou ecoa delimitadores de prompt injection).
  3. **Motor Acadêmico + Templates YAML + Exportador DOCX**: `TemplateRegistry` + `parse_text_to_blocks` + `build_docx` + `inspect_docx` validando o XML OpenXML gerado (`styles.xml`, `document.xml`, `settings.xml`) para todos os 8 tipos de template ABNT e perfis UFMS/UFGD.
  4. **Motor de Referências + Validador Acadêmico + DOIResolver**: `validate` + `parser` + `citation_parser` + `matcher` + `DOIResolver` (com `httpx.MockTransport`).

### 6.3 Testes de Integração (Topo — Fluxos Críticos Fim a Fim no Backend)
- **Escopo**: Rotas FastAPI (`TestClient`) + banco SQLite em memória/arquivo temporário (SQLAlchemy/Alembic) + armazenamento temporário (`tmp_path`):
  - Fluxo completo multi-usuário com `auth_enabled=True` e `credential_encryption_enabled=True`.
  - Contratos de erro padronizados (`HumanizaError.to_payload()`), validação estrita de schemas Pydantic (`extra="forbid"`, limites de tamanho), cabeçalhos HTTP e downloads binários.
  - Testes de migração Alembic (`upgrade head` → operações ORM → `downgrade base` → `upgrade head`).

---

## 7. GAPs e Achados Técnicos Identificados (Evidências no Código)

> **Regra de Escopo**: Conforme diretriz inegociável de QA, **nenhum arquivo de código da aplicação foi alterado**. Os bugs e vulnerabilidades abaixo foram confirmados por inspeção de código e devem ser cobertos por testes reprodutíveis na Fase B.

| ID | Categoria / GAP | Severidade | Evidência (Arquivo e Linhas) | Impacto Observado vs. Esperado | Recomendação |
|---|---|---|---|---|---|
| **GAP-01** | **Bug / Segurança (Cross-Tenant)**: `CredentialResolver._session` é global na aplicação e ignora `owner_id` | **Crítica** | `app/api/v1/providers.py:56-70, 124-127, 146-149`; `app/services/providers/credentials.py:105` | **Observado**: `app.state.provider_resolver` armazena chaves em `self._session[provider]` sem `owner_id`. Quando o Usuário A salva uma chave em `POST /providers/openai/credentials`, o Usuário B vê `configurado=True` e `last4` de A em `GET /providers`, pode deletar a chave da sessão de A e pode usá-la em `/humanize`. **Esperado**: Isolamento estrito por `owner_id` em sessão e banco. | Criar teste de integração multi-usuário em `tests/integration/test_providers_isolation_qa.py` provando o vazamento cross-tenant de `last4`/status. |
| **GAP-02** | **Bug Funcional**: Credenciais salvas em `PersistentCredentialStore` nunca são lidas pelo `ProviderRegistry.build()` | **Crítica** | `app/services/providers/registry.py:67-70`; `app/services/providers/persistent_credentials.py:18-66` | **Observado**: `PersistentCredentialStore` só possui `save`, `status` e `delete` (não tem `resolve`/`decrypt`). `ProviderRegistry.build()` chama apenas `self._resolver.resolve(enum)` (ambiente + memória). Se o servidor reiniciar ou a sessão em memória for limpa, a chave persistida no banco (`source="database"`) aparece como `configurado=True` em `GET /providers`, mas `build()` recebe `chave=""` e a chamada ao provedor falha por falta de chave. **Esperado**: `build()` deve resolver a chave persistida do `owner_id` no banco quando não houver chave em env/sessão. | Criar teste de componente/integração que salva credencial no banco, limpa `provider_resolver._session` e verifica a chave entregue ao adaptador em `registry.build()`. |
| **GAP-03** | **Bug / Segurança**: Rotas `/exports/**`, `/uploads` e `/humanize` não exigem autenticação quando `auth_enabled=True` nem isolam dados por `owner_id` | **Alta** | `app/api/v1/exports.py:71-298`; `app/api/v1/uploads.py:28-53`; `app/api/v1/humanize.py:48-105`; `app/models/export.py:14-35` | **Observado**: (1) Nenhuma rota de `exports.py`, `uploads.py` ou `humanize.py` declara `Depends(get_current_user)`. Com `auth_enabled=True`, requisições sem token `Bearer` têm sucesso (200/201). (2) `exports.py` usa `ExportHistoryStore` em memória sem `owner_id` (a tabela ORM `Export` em `app/models/export.py` nunca é usada em lugar nenhum do repositório!). O Usuário B consegue listar e baixar exportações do Usuário A. (3) Em `humanize.py:101`, `owner_id` vem do JSON enviado pelo cliente (`requisicao.owner_id`) em vez do token autenticado. **Esperado**: Exigir `get_current_user` quando `auth_enabled=True` e isolar exportações/uploads por `owner_id`. | Criar testes de segurança em `tests/integration/test_auth_enforcement_qa.py` documentando o acesso anônimo e cross-tenant em `/exports`, `/uploads` e `/humanize`. |
| **GAP-04** | **Bug / Segurança**: Bypass de Rate Limiting via falsificação de `X-Forwarded-For` | **Alta** | `app/core/ratelimit.py:40-47` | **Observado**: `client_ip(request)` lê `request.headers.get("x-forwarded-for")` incondicionalmente. Qualquer cliente que envie um header `X-Forwarded-For` diferente a cada requisição contorna completamente o limite de tentativas de login (`/auth/token`) e de `/humanize`. **Esperado**: Só confiar em `X-Forwarded-For` quando a conexão vier de um proxy reverso confiável configurável, ou limitar também por `username`/`user_id`. | Criar teste em `tests/integration/test_rate_limit_api.py` (ou novo arquivo QA) demonstrando o bypass por rotação de `X-Forwarded-For`. |
| **GAP-05** | **Bug / Arquitetura**: `store_upload` sobrescreve arquivos de mesmo nome e extração DOCX bloqueia o event loop | **Média** | `app/api/v1/uploads.py:44-45`; `app/services/ingestion/upload.py:64-70, 79-92` | **Observado**: (1) `store_upload` grava em `storage_dir/uploads/{sanitizado}` sem prefixar com o `id` único gerado na linha 48 (`new_id()`). Dois uploads com `artigo.txt` sobrescrevem o mesmo arquivo em disco. (2) `extract_text` para `.docx` executa `DocxDocument(BytesIO(data))` de forma síncrona dentro de `async def upload_documento`, bloqueando o event loop. | Criar teste verificando colisão de nomes no diretório de uploads e teste de extração de DOCX válido via `/api/v1/uploads`. |
| **GAP-06** | **Bug / Diagnóstico**: `/health` e `/health/readiness` ignoram `request.app.state.settings` e não testam conectividade real do banco | **Média** | `app/api/v1/health.py:14-35` (**73% de cobertura**, linhas 29–35 descobertas) | **Observado**: As rotas chamam `get_settings()` (cache global `@lru_cache`) em vez de `request.app.state.settings`, e `readiness()` retorna `"database": {"ok": True}` fixo sem consultar o banco. Além disso, `/health/readiness` não tem nenhum teste na suíte atual. | Criar testes para `/api/v1/health/readiness` cobrindo os estados `ok` e `degraded`. |
| **GAP-07** | **Lacuna de Cobertura / Heurística**: `semantic_validator` usa janela fixa de 80 chars (`_PROXIMIDADE`) sobre `source_range` para diferenciar `ALTERATION` de `LOSS` | **Média** | `app/services/semantic_validator/validator.py:26, 116-120` | **Observado**: Se a LLM expandir ou encurtar uma frase antes de uma entidade em mais de 80 caracteres e também alterar o valor da entidade, `vizinhas` fica vazia e a mudança é reportada como `LOSS` + `INVENTION` em vez de `ALTERATION`. | Criar testes unitários de fronteira para `_PROXIMIDADE` (distância exata de 80 vs. 81 code points) em `tests/unit/`. |
| **GAP-08** | **Lacuna de Testes**: Tabela `revisions` (`DocumentRevision`) e cascata de exclusão não são exercitadas via API | **Média** | `app/models/document.py:39-54`; `app/api/v1/documents.py:1-96` | **Observado**: O modelo ORM `DocumentRevision` existe, mas nenhuma rota da API cria ou consulta `DocumentRevision` no banco relacional. | Criar testes de repositório exercitando a criação de `DocumentRevision`, ordenação por `created_at` e `cascade="all, delete-orphan"` ao excluir `Document`. |
| **GAP-09** | **Risco de Licenciamento (R-38 / R-47)**: `pymupdf` (AGPL-3.0) como dependência obrigatória em projeto MIT | **Média** | `backend/pyproject.toml:21`; `docs/architecture/RISK_REGISTER.md:81, 104` | **Observado**: `RISK_REGISTER.md` classifica `PyMuPDF` (AGPL-3.0) como risco Alto aberto que deveria ser resolvido antes da Onda 6, mas `pymupdf>=1.24` permanece em `dependencies` de `pyproject.toml`. | Documentado como achado de auditoria para decisão do responsável pelo projeto. |

---

## 8. Avaliação de Testabilidade

| Item Avaliado | Evidência | Classificação | Observação |
|---|---|---|---|
| Injeção de Provedores de LLM e Transporte HTTP | `ProviderRegistry(..., transport=...)`, `HumanizerService(provider)` | **Não bloqueia os testes** | Excelente isolamento; permite uso de `FakeLLMProvider` e `httpx.MockTransport` sem rede. |
| Banco de Dados nos Testes | `conftest.py` (`db_engine` com SQLite `:memory:` e `StaticPool`) | **Não bloqueia os testes** | Rápido e determinístico. |
| Estado em `app.state` vs. `get_settings()` cacheado | `app/core/config.py:122` (`@lru_cache`), `app/api/v1/health.py:17, 29` | **Dificulta os testes** | Rotas que usam `get_settings()` diretamente ignoram `app.state.settings` sobrescrito nos fixtures; exige `get_settings.cache_clear()` ou `monkeypatch`. |
| Dependência de Relógio (`time.time`, `time.monotonic`, `datetime.now`) | `app/core/security.py:88, 114`, `app/core/ratelimit.py:29`, `app/api/v1/documents.py:92` | **Dificulta os testes** | `TokenService` e `SlidingWindowLimiter` usam `time.time()`/`time.monotonic()` diretamente; testes de expiração de janela exigem TTL negativo ou `monkeypatch` no módulo `time`. |
| Dependência de Binário Externo (LibreOffice `soffice`) | `app/services/document_export/pdf_builder.py` | **Não bloqueia os testes** | `build_pdf_from_docx` aceita `renderer="none"` ou binário inexistente, degradando graciosamente com declaração de limitação. |
| Estado Compartilhado em Memória (`_engine` em `normalize.py`, `provider_resolver` em `main.py`) | `app/api/v1/normalize.py:29`, `app/main.py:85` | **Requer decisão do time de desenvolvimento** | `_engine` é stateless (seguro), mas `provider_resolver` e `export_store` guardam estado mutável global em memória entre requisições no mesmo `app`. |

---

## 9. Estrutura Proposta para a Pasta de Testes (`backend/tests/`)

Mantendo total compatibilidade com a convenção existente em `backend/pyproject.toml` (`testpaths = ["tests"]`) e adicionando apenas os diretórios necessários:

```text
backend/tests/
├── conftest.py                  # Fixtures globais (DB em memória, apps configuradas)
├── docs/
│   └── Actions.md               # Este plano de ação e auditoria de QA
├── fixtures/                    # Textos acadêmicos reais anonimizados (regressão)
├── unit/                        # Testes unitários rápidos (regras, IR, segurança, parsers)
│   └── fakes.py                 # FakeLLMProvider e dublês determinísticos
├── component/                   # [NOVO] Testes de componente (pipelines completos sem HTTP)
├── integration/                 # Testes de integração (FastAPI TestClient + SQLite + FS)
└── regression/                  # Suíte de regressão documental científica e arquitetural
```

---

## 10. Configuração Inicial da Suíte

- **Comando de execução padrão**:
  ```bash
  cd backend && .venv/bin/pytest --cov=app --cov-report=term-missing
  ```
- **Verificações estáticas obrigatórias antes de concluir qualquer etapa** (`AGENTS.md` §3.15):
  ```bash
  cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy
  ```
- **Política de Warnings e Rede**:
  - `filterwarnings = ["error"]` está ativo em `pyproject.toml`: nenhum teste pode emitir `DeprecationWarning` ou `ResourceWarning`.
  - Zero chamadas de rede externa: usar sempre `FakeLLMProvider` (`tests/unit/fakes.py`) ou `httpx.MockTransport`.

---

## 11. Backlog Priorizado

### P0 — Fundação e Guardas Arquiteturais
- Testes de fronteira arquitetural (`ADR-0002`): garantir via análise de AST/imports que `app/services/academic/**` nunca importa `app/services/providers/**`, `app/services/providers/**` nunca importa `app/services/academic/**` e `app/services/normalizer/**` nunca importa `app/services/providers/**`.
- Testes de prontidão (`/api/v1/health/readiness`) cobrindo estados `ok` e `degraded`.

### P1 — Fluxos Críticos, Segurança e Reprodução de Bugs Confirmados (GAP-01 a GAP-05)
- Testes reproduzindo ou auditando o isolamento multi-tenant de credenciais (`GAP-01`) e a resolução de credenciais persistidas no banco (`GAP-02`).
- Testes auditando o controle de acesso (`auth_enabled=True`) e isolamento em `/api/v1/exports`, `/api/v1/uploads` e `/api/v1/humanize` (`GAP-03`).
- Testes de segurança de rate limiting em `/api/v1/humanize` e auditoria do comportamento com `X-Forwarded-For` (`GAP-04`).
- Testes completos de upload DOCX válido, DOCX corrompido, arquivo binário com byte NUL, UTF-8 inválido e colisão de nomes (`GAP-05`).

### P2 — Regras de Negócio e Casos de Fronteira (Unitários)
- Testes de fronteira do `semantic_validator` (`_PROXIMIDADE = 80` vs `81`, entidades sem fingerprint, múltiplas invenções e alterações simultâneas).
- Testes unitários das linhas não cobertas em `app/ir/protection.py`, `app/ir/document.py`, `app/ir/spans.py` e `app/ir/blocks.py`.
- Testes unitários para casos de borda dos parsers de referências (`bibtex.py`, `csl_json.py`, `parser.py`, `nbr6023.py`, `matcher.py`).

### P3 — Testes de Componente (`backend/tests/component/`)
- Pipeline completo `NormalizationEngine` + `HumanizerService` (com `FakeLLMProvider`) + `AcademicValidator` + `build_docx` operando em sequência sobre um mesmo `AcademicDocument`, verificando invariância de `original_text` e acumulação de `DocumentRevision`.

### P4 — Integração de Persistência e Migrações
- Teste automatizado do ciclo Alembic (`upgrade head` → `downgrade base` → `upgrade head`) em banco SQLite temporário.
- Testes de repositório e cascata ORM para `Document` + `DocumentRevision` e `CredentialRepository.list_for_owner`.

### P5 — Robustez, Idempotência e Concorrência
- Teste de idempotência de todas as 29 regras de normalização aplicadas duas vezes seguidas (`f(f(x)) == f(x)`).
- Teste de concorrência thread-safe no `SlidingWindowLimiter` (múltiplas threads simultâneas batendo no limite exato).
- Teste de retenção (`prune_expired`) em `ExportHistoryStore` removendo arquivos físicos vencidos do disco e preservando os vigentes.

---

## 12. Passo a Passo Granular para o Próximo Agente (Fase B)

| Ordem | ID | Prioridade | Ação Executável | Tipo | Arquivo(s) Alvo | Critério de Aceite Objetivo |
|---|---|---|---|---|---|---|
| 1 | ACT-01 | P0 | Criar teste de arquitetura verificando via `ast` que nenhum módulo em `app/services/academic/` ou `app/services/normalizer/` importa `app/services/providers/` (e vice-versa), conforme `ADR-0002` e Risco `R-37`. | Regressão | `backend/tests/regression/test_architecture_boundaries.py` | Teste inspeciona todos os `.py` de `app/services/` e passa com 0 violações. |
| 2 | ACT-02 | P0 | Criar testes de integração para `GET /api/v1/health/readiness` cobrindo o retorno `status == "ok"` (quando `templates_dir` existe) e `status == "degraded"` (usando `monkeypatch` em `get_settings` com `templates_dir` inexistente). | Integração | `backend/tests/integration/test_api_smoke.py` | Cobertura de `app/api/v1/health.py` sobe de 73% para 100%. |
| 3 | ACT-03 | P1 | Criar testes de integração para o rate limiter na rota `POST /api/v1/humanize` (além do de login já existente) verificando retorno HTTP 429 (`rate_limit_exceeded`) ao exceder a janela, e teste documentando o comportamento de `X-Forwarded-For` (`GAP-04`). | Integração | `backend/tests/integration/test_rate_limit_api.py` | Teste exercita o limiter `"humanize"` com HTTP 429 e valida o payload de erro padronizado. |
| 4 | ACT-04 | P1 | Criar testes de integração para `POST /api/v1/uploads` cobrindo: (a) upload de um `.docx` real gerado em memória por `python-docx` extraindo parágrafos corretamente; (b) rejeição de `.txt` com byte NUL (`\x00`) com HTTP 422; (c) rejeição de `.txt` com bytes Latin-1/inválidos em UTF-8 com HTTP 422 (`GAP-05`). | Integração | `backend/tests/integration/test_uploads_api.py` | Cobertura de `app/services/ingestion/upload.py` sobe de 87% para >= 98%. |
| 5 | ACT-05 | P1 | Criar suíte de auditoria de isolamento e persistência de credenciais (`GAP-01` e `GAP-02`): testar `CredentialRepository.list_for_owner` (com `owner_id=None` e `owner_id="user-1"`), `PersistentCredentialStore` quando `cipher.available` é `False` (lançando `ValidationError`), e `POST /api/v1/providers/openai/credentials` quando a chave já vem de `env` (não sobrescrevendo). | Unitário / Integração | `backend/tests/unit/test_persistent_credentials.py`, `backend/tests/integration/test_providers_api.py` | Cobertura de `app/repositories/credentials.py`, `app/services/providers/persistent_credentials.py` e `app/api/v1/providers.py` >= 96%. |
| 6 | ACT-06 | P1 | Criar testes de integração para `GET /api/v1/auth/me` e `get_current_user` cobrindo: (a) usuário inativo (`is_active=False`) retornando 401; (b) `token_service=None` com `auth_enabled=True` retornando 401; (c) chamada a `/api/v1/auth/me` com `auth_enabled=False` retornando 401; (d) `POST /api/v1/auth/token` com `token_service=None` retornando 401. | Integração | `backend/tests/integration/test_auth_api.py` | Cobertura de `app/api/deps.py` e `app/api/v1/auth.py` sobe para 100%. |
| 7 | ACT-07 | P2 | Criar testes unitários de fronteira para `app/services/semantic_validator/validator.py`: (a) entidade alterada na distância exata de 80 code points (`ALTERATION`) vs. 81 code points (`LOSS` + `INVENTION`) (`GAP-07`); (b) entidades de níveis `HIGH`, `MEDIUM` e `LOW` (`_severidade_por_nivel`); (c) propriedade `ValidationReport.has_critical`. | Unitário | `backend/tests/unit/test_semantic_validator.py` | Cobertura de `app/services/semantic_validator/validator.py` sobe de 91% para 100%. |
| 8 | ACT-08 | P3 | Criar teste de componente fim a fim em `backend/tests/component/test_full_pipeline_component.py` encadeando: `NormalizationEngine.run()` → `HumanizerService.humanize()` (com `FakeLLMProvider`) → `references.validator.validate()` → `build_docx()` → `ExportHistoryStore.record_export()` sobre um `AcademicDocument`, validando imutabilidade de `original_text` e rastreabilidade de `transformations`. | Componente | `backend/tests/component/test_full_pipeline_component.py` | Pipeline completo de domínio executa em < 200ms sem HTTP e valida invariantes do IR (`ADR-0003`). |
| 9 | ACT-09 | P4 | Criar testes de persistência para `DocumentRevision` (criação vinculada a `Document`, leitura via `document.revisions` e exclusão em cascata ao deletar o documento) e teste de retenção real via `POST /api/v1/documents/prune` removendo documento com `updated_at` retroativo no banco (`GAP-08`). | Unitário / Integração | `backend/tests/unit/test_documents_repository.py`, `backend/tests/integration/test_documents_api.py` | `POST /api/v1/documents/prune` retorna `removidos == 1` para documento expirado e `DocumentRevision` é removida em cascata. |
| 10 | ACT-10 | P4 | Criar teste de integração executando as migrações Alembic (`command.upgrade(cfg, "head")`, inspeção das 5 tabelas via `sqlalchemy.inspect`, `command.downgrade(cfg, "base")`, `command.upgrade(cfg, "head")`) contra um banco SQLite em `tmp_path`. | Integração | `backend/tests/integration/test_alembic_migrations.py` | Migração `0001_inicial` testada automaticamente na suíte `pytest` (upgrade e downgrade limpos). |
| 11 | ACT-11 | P5 | Criar testes de robustez: (a) concorrência em `SlidingWindowLimiter` com `ThreadPoolExecutor(max_workers=8)` disparando 50 requisições simultâneas para `limit=10` e garantindo exatamente 10 aprovações; (b) `ExportHistoryStore.prune_expired()` removendo exportações antigas do disco e preservando as recentes. | Unitário | `backend/tests/unit/test_ratelimit.py`, `backend/tests/unit/test_export_writer.py` | Testes determinísticos, sem `sleep`, validando thread-safety e limpeza de disco. |
| 12 | ACT-12 | P0–P5 | Executar `ruff check .`, `ruff format --check .`, `mypy`, `pytest --cov=app` e `git status` para confirmar que 100% dos testes passam e nenhum arquivo fora de `backend/tests/` foi modificado. | Verificação | `backend/tests/` | 0 erros em lint/typecheck/pytest; `git status` mostra alterações apenas em `backend/tests/`. |

---

## 13. Fase B — Resolução dos GAPs (executada pelo agente de desenvolvimento)

> Diferentemente do agente de QA (restrito a `backend/tests/`), o agente de
> desenvolvimento **alterou o código da aplicação** para eliminar os bugs e
> vulnerabilidades confirmados. Status em **2026-10-22**.

| GAP | Ação de correção (arquivo) | Teste de regressão que prova a correção |
|---|---|---|
| **GAP-01** cross-tenant de credenciais em sessão | `CredentialResolver` agora indexa a sessão por `(owner_id, provider)`; rotas passam o `owner_id` do usuário autenticado | `tests/integration/test_providers_isolation_qa.py::test_credencial_de_sessao_isolada_por_usuario` |
| **GAP-02** credencial persistida nunca lida pelo `build()` | `PersistentCredentialStore.resolve_plaintext` + `ProviderRegistry.build(api_key=...)` + `resolve_provider_key` na camada de API | `test_persistent_store_isolado_por_usuario`, `test_registry_build_usa_chave_explicita` |
| **GAP-03** rotas `/exports`, `/uploads`, `/humanize` sem auth/isolamento | `get_current_user` + `owner_id` em todas as rotas; `ExportRecord`/`ExportHistoryStore` isolados por dono; `humanize` usa `owner_id` do token | `tests/integration/test_auth_enforcement_qa.py` |
| **GAP-04** bypass de rate limit via `X-Forwarded-For` | `client_ip` só confia no cabeçalho quando `Settings.behind_proxy=True` | `test_rate_limit_api.py::test_rate_limit_nao_e_contornado_por_x_forwarded_for` |
| **GAP-05** colisão de nome + DOCX síncrono no upload | nome único (`{id}_{sanitizado}`) + `asyncio.to_thread` na extração DOCX + isolamento por diretório de dono | `test_uploads_api.py::test_upload_docx_extrai_paragrafos`, `test_upload_mesmo_nome_nao_sobrescreve` |
| **GAP-06** `/health/readiness` ignora `app.state.settings` e não checa banco | usa `request.app.state.settings` + `SELECT 1` real | `test_api_smoke.py::test_readiness_ok`, `test_readiness_degraded_sem_templates` |
| **GAP-07** janela fixa `_PROXIMIDADE=80` | comportamento documentado em testes de fronteira (80 vs. 81) | `test_semantic_validator.py::test_proximidade_80/81_*` |
| **GAP-08** `revisions`/cascade não exercitados | teste de repositório de `DocumentRevision` + cascata | `test_documents_repository.py::test_revisao_vinculada_e_removida_em_cascata` |
| **GAP-09** `pymupdf` AGPL obrigatório | dependência movida para extra `pdf` + import lazy com degradação graciosa | `ADR-0016` |

**Resultado final**: `ruff check`, `ruff format --check`, `mypy` e `pytest`
(484 testes) todos verdes; cobertura global de 96%.
