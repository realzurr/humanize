# Onda 0 — Análise e Preparação

- **Data**: 2026-10-21
- **Escopo**: análise do repositório de referência, levantamento de riscos e
  dependências, definição da arquitetura, do IR e do fluxo de dados, criação
  do esqueleto do repositório e das ADRs.
- **Status**: concluída. Nenhuma funcionalidade de usuário foi implementada.

---

## 1. Escopo executado

| # | Entregável do ROADMAP | Onde | Estado |
|---|---|---|---|
| 1 | Análise do repositório de referência + riscos | `docs/architecture/REFERENCE_REPO_ANALYSIS.md` | ✅ |
| 2 | Levantamento de dependências e riscos | `docs/architecture/RISK_REGISTER.md` (R-01…R-49) | ✅ |
| 3 | Requisitos funcionais e não funcionais | `docs/ROADMAP.md` §1 (RF-01…RF-17, RNF-01…RNF-12) | ✅ |
| 4 | Módulos e interfaces definidos | `app/ir/`, `app/services/providers/base.py`, `app/services/normalizer/rules/base.py` | ✅ |
| 5 | Arquitetura e fluxo de dados | `docs/ARCHITECTURE.md` | ✅ |
| 6 | Modelos de documento intermediário | `app/ir/{spans,blocks,protection,document}.py` | ✅ |
| 7 | Estratégia de preservação de conteúdo | `docs/ARCHITECTURE.md` §4 | ✅ |
| 8 | Estrutura inicial do repositório | árvore da raiz | ✅ |
| 9 | README | `README.md` | ✅ |
| 10 | Arquitetura | `docs/ARCHITECTURE.md` | ✅ |
| 11 | Roadmap | `docs/ROADMAP.md` | ✅ |
| 12 | Decisões | `docs/DECISIONS.md` + `docs/decisions/ADR-0001…ADR-0015` | ✅ |
| 13 | Regras permanentes | `AGENTS.md` | ✅ |
| 14 | Toolchain verificada (ruff/mypy/pytest verdes) | `backend/pyproject.toml` | ✅ |

Além do escopo planejado, foram executadas duas correções de integridade
do repositório, descritas na §2.

## 2. Funcionalidades concluídas

Nenhuma funcionalidade de usuário — a Onda 0 entrega apenas arquitetura,
contratos e ferramentas. O que foi efetivamente construído:

- **IR (`app/ir/`)**: `TextSpan`, `BlockKind`, `Block`, `ProtectedEntity`,
  `ProtectionCatalog` e `AcademicDocument` (imutável, com `original_text`,
  `revisions` append-only e `with_revision()`). Fingerprint de normalização
  para detecção de perda de informação.
- **Contratos de serviço**: `BaseProvider` (provedores de LLM) e
  `BaseRule`/`BaseNormalizer` (normalização determinística), com as proibições
  de acoplamento `P1`–`P7` já codificadas.
- **API mínima**: `GET /api/v1/health` e `GET /api/v1/health/readiness`,
  prefixo `/api/v1`, erros de domínio via `HumanizaError`.
- **Observabilidade**: `structlog` com o processor `redact_secrets` obrigatório.
- **Frontend**: esqueleto de navegação (React + Vite + TypeScript + Tailwind)
  com as 11 rotas previstas, sem telas funcionais (previsto para a Onda 7).
- **Templates**: esquema JSON (`templates/schemas/template.schema.json`) e
  template-base `templates/abnt/general/general.yaml`.
- **Infraestrutura**: `docker-compose.yml`, `backend/Dockerfile`,
  `frontend/Dockerfile`, `frontend/nginx.conf`.

### Correções de integridade executadas nesta onda

1. **De-corrupção textual do repositório.** O repositório sofreu uma
   corrupção sistemática de acentuação (inserção de acentos indevidos em
   prosa, comentários, chaves de log e identificadores). A reversão foi
   feita por comparação com o snapshot pré-corrupção do índice do Git, e
   não por substituição às cegas: cada hunk foi revisado individualmente.
   O identificador corrompido `ré.sub` em `app/ir/protection.py` foi
   restaurado, e o arquivo está hoje idêntico ao snapshot.
2. **Normalização ortográfica pt-BR da documentação.** Os ADRs foram
   escritos sem acentuação. A correção usou um dicionário curado de 908
   entradas (363 correções efetivas), validado contra o dicionário hunspell
   `pt_BR` (2,8 milhões de formas expandidas a partir de
   `pt_BR.aff`/`pt_BR.dic`). Identificadores, rotas, chaves de JSON/YAML,
   nomes de pacote e URLs foram preservados intactos por construção.

## 3. Arquivos criados ou modificados

- **Documentação**: `AGENTS.md`, `README.md`, `docs/ARCHITECTURE.md`,
  `docs/ROADMAP.md`, `docs/DECISIONS.md`, `docs/architecture/{REFERENCE_REPO_ANALYSIS,RISK_REGISTER}.md`,
  `docs/standards/ABNT_NORMS_RESEARCH.md`, `docs/decisions/ADR-0001…ADR-0015.md`,
  `docs/waves/onda-0.md` (este relatório).
- **Backend**: `backend/app/{main.py}`, `backend/app/core/{config,errors,logging}.py`,
  `backend/app/api/router.py`, `backend/app/api/v1/health.py`,
  `backend/app/ir/{spans,blocks,protection,document}.py`,
  `backend/app/services/normalizer/rules/base.py`,
  `backend/app/services/providers/base.py`, `backend/app/{models,repositories,schemas}/__init__.py`,
  `backend/pyproject.toml`, `backend/Dockerfile`.
- **Testes**: `backend/tests/unit/{test_ir,test_logging}.py`,
  `backend/tests/integration/test_api_smoke.py`.
- **Frontend**: `frontend/src/{main.tsx,App.tsx,vite-env.d.ts}`,
  `frontend/src/{services/api.ts,types/index.ts,hooks/useSaude.ts,styles/index.css}`,
  `frontend/{package.json,package-lock.json,vite.config.ts,tsconfig.json,tailwind.config.js,postcss.config.js,index.html}`,
  `frontend/nginx.conf`, `frontend/Dockerfile`.
- **Templates**: `templates/schemas/template.schema.json`,
  `templates/abnt/general/general.yaml`, `templates/README.md`.
- **Infra**: `docker-compose.yml`, `.env.example`, `.gitignore`.

## 4. Testes realizados

| Suíte | Arquivo | Testes | Resultado |
|---|---|---|---|
| Unitário — IR | `backend/tests/unit/test_ir.py` | 19 | 19 passaram |
| Unitário — logging | `backend/tests/unit/test_logging.py` | 7 | 7 passaram |
| Integração — API | `backend/tests/integration/test_api_smoke.py` | 3 | 3 passaram |
| **Total** | | **29** | **29 passaram** |

Verificações estáticas e de build:

| Verificação | Resultado |
|---|---|
| `ruff check .` | All checks passed |
| `ruff format --check .` | 35 files already formatted |
| `mypy .` (modo `strict`) | Success: no issues found in 35 source files |
| `pytest -q` | 29 passed in 0.29s |
| `npx tsc --noEmit` | sem erros |
| `npx vite build` | ✓ built in 912ms |
| API ao vivo (`uvicorn`) | `/api/v1/health` e `/api/v1/health/readiness` → `200`/`ok` |

## 5. Resultados obtidos (com saída real dos comandos)

```
$ ruff check .
All checks passed!

$ ruff format --check .
35 files already formatted

$ mypy .
Success: no issues found in 35 source files

$ pytest -q
.............................                                            [100%]
29 passed in 0.29s

$ npx tsc --noEmit
(sem saída — nenhum erro de tipo)

$ npx vite build
dist/index.html                   0.54 kB │ gzip:  0.34 kB
dist/assets/index-CU8e1tfv.css    6.79 kB │ gzip:  1.96 kB
dist/assets/index-CicQ2Ujg.js   169.21 kB │ gzip: 55.45 kB │ map: 714.77 kB
✓ built in 912ms

$ curl -s localhost:8099/api/v1/health
{"status":"ok","app":"Humaniza Acadêmico","version":"0.1.0","environment":"local"}

$ curl -s localhost:8099/api/v1/health/readiness
{"status":"ok","checks":{"database":{"ok":true,"detail":"configurado"},
 "templates":{"ok":true,"detail":".../templates"}}}
```

Acessibilidade de segurança verificada: o `redact_secrets` mascara
`api_key`, `Authorization` e `TOKEN`, e redige segredos embutidos em texto
livre (testes `test_redact_secrets_devolve_o_event_dict`,
`test_cadeia_com_renderer_renderiza_json`,
`test_configure_logging_nao_vaza_segredo`).

## 6. Pendências

| Pendência | Onda | Observação |
|---|---|---|
| Licença definitiva do projeto (código, templates, documentação) | decisão do responsável | `ADR-0014` está como *Proposta*; nenhum arquivo `LICENSE` foi adicionado |
| `PyMuPDF` (AGPL-3.0) no `backend/` | 6 | `R-38` e `R-47` abertos; avaliar `pypdf`/`pdfplumber` |
| Renderizador de PDF no ambiente | 6 | `R-39`; `weasyprint` declarado como extra `pdf` |
| Emenda 05/2025 da NBR 6023:2025 | 5 | teor não lido nesta rodada (`P-07`) |
| Permalinks oficiais por norma (site ABNT inacessível a fetch automatizado) | 4/5 | `P-01` |
| Manuais institucionais vigentes da UFMS/UFGD | 4 | `P-02`, `P-03`; sem conformidade presumida |
| `jsonschema` como dependência de desenvolvimento | 4 | validação real do template ainda manual |
| Indireção de chave por cofre (`*_API_KEY_ENV_NAME`) | 8 | registrada em `docs/ROADMAP.md` §3 |
| Suíte do frontend (Vitest + Testing Library) | 7 | dependências declaradas, sem teste escrito |

## 7. Riscos conhecidos

- **R-01** — NFKC destrói superíndices/índices (`10⁻⁶` → `10-6`). Mitigação
  projetada: NFKC desligado por padrão, com lista de exceções.
- **R-05** — U+2212 (sinal de menos) convertido em hífen.
- **R-10** — NFKC e limpeza de Markdown interferem entre si.
- **R-15** — Texto importado contém instrução (prompt injection). O texto
  importado é conteúdo delimitado, nunca instrução.
- **R-38 / R-47** — Dependência AGPL (`PyMuPDF`) em produto de licença
  proprietária. Bloqueia a Onda 6.
- **R-44** — O usuário pode confundir o relatório de conformidade com
  certificação. O relatório declara conformidade **por regra**, com fonte e
  grau de confiabilidade.
- **R-46** — Contágio GPL-3.0 por contato com o repositório de referência.
  Mitigado: reimplementação *clean-room* (`ADR-0001`); nenhum arquivo do
  repositório de referência foi copiado.
- **R-48** — Licença do projeto indefinida atrasa a distribuição.

Registro completo em `docs/architecture/RISK_REGISTER.md` (R-01…R-49).

## 8. Próxima onda recomendada

**Onda 1 — Normalização Textual** (`docs/ROADMAP.md`): motor de
normalização determinístico, sem LLM, com regras parametrizadas e
versionadas, relatório por regra e teste de regressão documental com
textos-fixture versionados.

A Onda 1 **não** deve ser iniciada sem autorização expressa do responsável
pelo projeto, conforme a regra dura do `AGENTS.md`.

## 9. Limitações declaradas

1. **Nenhuma funcionalidade de usuário foi implementada.** A API expõe
   apenas `/api/v1/health` e `/api/v1/health/readiness`; o frontend é
   esqueleto de navegação. A Onda 0 entrega arquitetura, contratos e
   ferramentas — nada mais.
2. **Nenhuma chamada a LLM pago foi realizada** durante a onda. Os contratos
   de provedor existem, mas nenhuma implementação real foi exercitada.
3. **Nenhum serviço foi instalado ou modificado em servidor externo.**
4. **O ambiente não possui as dependências de PDF** (`weasyprint`,
   `PyMuPDF`); os testes de exportação da Onda 6 dependem disso.
5. **A validação do schema de template é manual.** `jsonschema` não está
   instalado; as chaves obrigatórias foram conferidas à mão, e a validação
   real fica para a Onda 4.
6. **A norma ABNT não é reproduzida na íntegra** — apenas a estrutura e as
   regras, com fonte, edição, URL e data de consulta
   (`docs/standards/ABNT_NORMS_RESEARCH.md`).
7. **A conformidade com manuais institucionais não é presumida.** Onde o
   manual da instituição diverge da norma geral, o conflito é registrado no
   relatório de conformidade, não resolvido silenciosamente (`ADR-0007`).
8. **A de-corrupção textual não é verificável por teste automatizado.** O
   snapshot original não faz parte do repositório (por decisão de
   clean-room), então a verificação foi feita por diff contra o índice do
   Git, arquivo a arquivo, durante esta onda.
9. **A acentuação da documentação foi normalizada, mas não houve revisão
   editorial completa.** Passagens longa de prosa (por exemplo, os
   argumentos do `ADR-0001`) podem conter ainda construções a revisar em
   ondas futuras.
