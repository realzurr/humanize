# Roadmap — Humaniza Acadêmico

> Plano de ondas. Cada onda é executada **apenas** com autorização expressa do
> responsável pelo projeto. Detalhes de escopo, entregáveis e critérios de
> aceite estão aqui; o estado técnico está em `docs/waves/`.

---

## 0. Visão geral das ondas

| Onda | Nome | Depende de | Entrega principal | Estado |
|---|---|---|---|---|
| 0 | Análise e Preparação | — | Arquitetura, IR, tooling, documentação | ✅ concluída |
| 1 | Normalização Textual | 0 | Motor de limpeza sem LLM + API + UI mínima | ✅ concluída |
| 2 | Integração Multi-LLM | 1 | `LLMProvider` + 5 adaptadores + resiliência | ✅ concluída |
| 3 | Humanização Semântica | 2 | Motor de revisão + perfis + validação | ✅ concluída |
| 4 | Sistema de Templates ABNT | 1 | Templates versionados + gerador de estrutura | ✅ concluída |
| 5 | Citações, Referências e Validador | 3, 4 | NBR 6023/10520 + relatórios auditáveis | ✅ concluída |
| 6 | Geração de Documentos | 4, 5 | DOCX nativo + PDF + histórico | ⛔ aguardando |
| 7 | Interface e Experiência | 1–6 | 11 páginas + editor comparativo | ⛔ aguardando |
| 8 | Segurança, Testes e Estabilização | 7 | Auth, isolamento, E2E, docs de deploy | ⛔ aguardando |

**Paralelismo possível:** a Onda 4 depende apenas da Onda 1 (normalização) e do
IR; pode ser iniciada enquanto a Onda 3 ainda está em curso, **desde que**
nenhuma das duas altere `app/ir/` sem coordenação.

---

## Onda 0 — Análise e Preparação ✅

**Objetivo:** estabelecer a arquitetura antes da implementação.

### Entregáveis

| # | Item | Onde |
|---|---|---|
| 1 | Análise do repositório de referência + riscos | `docs/architecture/REFERENCE_REPO_ANALYSIS.md` |
| 2 | Levantamento de dependências e riscos | `docs/architecture/RISK_REGISTER.md` |
| 3 | Requisitos funcionais e não funcionais | `docs/ROADMAP.md` (seção 1) |
| 4 | Módulos e interfaces definidos | `app/ir/`, `app/services/providers/base.py`, `app/services/normalizer/rules/base.py` |
| 5 | Arquitetura e fluxo de dados | `docs/ARCHITECTURE.md` |
| 6 | Modelos de documento intermediário | `app/ir/{spans,blocks,protection,document}.py` |
| 7 | Estratégia de preservação de conteúdo | `docs/ARCHITECTURE.md` §4 |
| 8 | Estrutura inicial do repositório | árvore do repositório |
| 9 | README | `README.md` |
| 10 | Arquitetura | `docs/ARCHITECTURE.md` |
| 11 | Roadmap | `docs/ROADMAP.md` |
| 12 | Decisões | `docs/DECISIONS.md` + `docs/decisions/` |
| 13 | Regras permanentes | `AGENTS.md` |
| 14 | Toolchain verificada (ruff/mypy/pytest verdes) | `backend/pyproject.toml` |

### Critérios de aceite (verificados)

- [x] Arquitetura documentada com fluxo de dados e camadas
- [x] Árvore inicial de diretórios criada
- [x] Plano das 8 ondas com escopo, entregáveis e critérios de aceite
- [x] Decisão de licenciamento registrada com justificativa
- [x] `ruff check` sem erros
- [x] `ruff format --check` sem erros
- [x] `mypy --strict` sem erros
- [x] `pytest` verde (29 testes)
- [x] Nenhuma chamada a LLM pago realizada
- [x] Nenhum serviço instalado em servidor externo
- [x] Nenhuma funcionalidade de usuário implementada

---

## Onda 1 — Normalização Textual ✅

**Objetivo:** implementar o primeiro motor do sistema, sem utilizar LLM.

### Escopo

**Backend** (`app/services/normalizer/`):
- `engine.py` — pipeline determinístico de regras.
- `rules/` — uma classe por transformação, cada uma com `rule_id` estável.
- `protect.py` — segmentação do texto em trechos protegidos e livres.
- `profile.py` — `NormalizationProfile` (configuração por conjunto de regras).
- `stats.py` — `NormalizationReport` (contagens por regra e categoria).
- `schemas/normalize.py` — request/response Pydantic.
- `api/v1/normalize.py` — `POST /api/v1/normalize`.

**Frontend** (mínimo, em `pages/Normalizacao.tsx`):
- Editor de entrada com contador de caracteres.
- Checkbox por opção: NFKC, invisíveis, emojis, Markdown, espaços.
- Painel de saída lado a lado com destaque das alterações.
- Estatísticas por regra.
- Botão de copiar; exportação TXT e Markdown.

### Regras esperadas (com `rule_id` provisório)

| `rule_id` | Descrição | Risco acadêmico |
|---|---|---|
| `norm.invisible.zwsp` | ZWSP/ZWJ/ZWNJ/BOM/word-joiner | Baixo |
| `norm.invisible.bidi` | Caracteres de controle bidirecional | Médio — pode inverter a ordem de exibição |
| `norm.invisible.soft_hyphen` | Hífen opcional | Baixo |
| `norm.invisible.variation` | Seletores de variação e ZWJ de emoji | Baixo |
| `norm.unicode.nfkc` | Normalização Unicode (NFKC) | **Alto** — ver §4.1 |
| `norm.unicode.nfc` | Composição canônica (NFC) | Baixo |
| `norm.whitespace.nbsp` | Espaços não separáveis → espaço | Baixo |
| `norm.whitespace.collapse` | Sequências de espaços → 1 | Baixo |
| `norm.whitespace.trailing` | Espaços no fim da linha | Baixo |
| `norm.whitespace.blank_lines` | 3+ linhas em branco → 2 | Baixo |
| `norm.punctuation.space_before` | Espaço antes de pontuação | Baixo |
| `norm.markdown.*` | Limpeza de Markdown | **Alto** — ver §4.2 |
| `norm.emoji.remove` | Remoção de emoji | **Alto** — remove `©`, `®`, `™` |
| `norm.pseudographics` | Pseudo-gráficos de caixa → ASCII | Médio — ver §4.3 |
| `norm.dash.normalize` | Traços → hífen | **Alto** — U+2212 é sinal de menos |
| `norm.quotes.ascii` | Aspas curvas → retas | Médio — afeta citação literal |
| `norm.ellipsis.ascii` | `…` → `...` | Baixo |
| `norm.bullet.normalize` | Marcadores → `-` | Baixo |
| `norm.control.strip` | Caracteres de controle C0/C1 | Baixo |
| `norm.ansi.strip` | Sequências de escape ANSI | Baixo |
| `norm.html.entities` | Decodificação de entidades HTML | Médio |

### Requisitos críticos (preservação)

O motor **não pode** remover nem alterar automaticamente:

- Referências bibliográficas · DOI e URL · Citações · Fórmulas matemáticas ·
  Unidades e valores numéricos · Símbolos científicos necessários ·
  Tabelas estruturadas · Código-fonte em blocos identificados.

> **⚠️ Risco conhecido (herdado do repositório de referência):** NFKC
> converte `²` → `2`, `³` → `3` e `10⁻⁶` → `10-6`, destruindo notação
> científica. A regra `norm.unicode.nfkc` deve ser **desligada por padrão**
> ou operar com uma lista de exceções, e o teste de regressão deve cobrir
> `10⁻⁶`, `x²`, `Na⁺` e `CO₂`.

### Critérios de aceite

- [x] Cada regra tem teste unitário próprio, incluindo o caso "não faz nada"
      quando desabilitada.
- [x] Existe uma suíte de regressão documental (`tests/fixtures/`) com textos
      acadêmicos reais anonimizados, contendo: fórmulas, unidades, tabelas,
      bloco de código, citação literal, DOI, referência, superíndices,
      subscritos e alfabeto grego.
- [x] O teste de regressão verifica explicitamente que trechos protegidos
      (números, fórmulas, superíndices, DOI, citações) permanecem intactos —
      a proteção é testada, não apenas a ausência de erro.
- [x] `POST /api/v1/normalize` devolve texto, relatório por regra e as
      entidades protegidas detectadas.
- [x] Exportação TXT e Markdown funcionam no frontend.
- [x] Nenhum teste exige chave de API nem chamada de rede.
- [x] `ruff check`, `ruff format --check`, `mypy`, `pytest` verdes;
      cobertura ≥ 80% em `app/services/normalizer/`.
- [x] Documentação atualizada: `docs/ARCHITECTURE.md` (mapa de regras),
      `docs/ROADMAP.md` (estado) e `docs/waves/onda-1.md`.

---

## Onda 2 — Integração Multi-LLM ✅

**Objetivo:** adicionar provedores de linguagem por uma interface comum.

### Escopo

- `app/services/providers/base.py` (já existe — contrato).
- `registry.py` — resolução de provedor por id; catálogo de adaptadores.
- `openai_provider.py`, `anthropic_provider.py`, `gemini_provider.py`,
  `ollama_provider.py`, `openai_compat.py` (compatível com API OpenAI).
- `credentials.py` — resolução de chave (env, banco cifrado, sessão).
- `resilience.py` — timeout, retry com backoff exponencial + jitter,
  respeito a `Retry-After`, tratamento de rate limit.
- `usage.py` — contagem de tokens e estimativa de custo.
- `api/v1/providers.py` — `GET /providers`, `GET /providers/{id}/models`,
  `POST /providers/{id}/credentials` (devolve só `configured`/`last4`),
  `DELETE /providers/{id}/credentials`.

### Requisitos de segurança

- Chave nunca em código, fixture, log ou resposta de API.
- Credencial persistida cifrada com AES-GCM (`cryptography`), chave fora do
  banco.
- `localStorage`/`sessionStorage` **nunca** guardam segredo.
- Ollama funciona sem chave externa.
- Documento importado é **conteúdo**, nunca instrução: delimites explícitos
  e instrução de sistema que proíbe seguir comandos do texto.

### Critérios de aceite

- [x] Uma mesma requisição (mesmo `LLMRequest`) roda com sucesso em **dois
      provedores distintos** (OpenAI + Ollama) com contrato idêntico de
      entrada e saída.
- [x] Timeout, retry com backoff, rate limit e resposta inválida têm teste
      com *fake provider* (sem rede).
- [x] Teste garante que a chave **não** aparece em log, exceção nem resposta
      JSON.
- [x] A API informa quando o modelo selecionado não está disponível
      (`MODEL_NOT_FOUND`).
- [x] Estimativa de tokens e custo exposta na resposta.
- [x] Cancelamento de requisição funciona onde o provedor suporta.
- [x] `ruff check`, `ruff format --check`, `mypy`, `pytest` verdes;
      cobertura ≥ 80% em `app/services/providers/`.
- [x] Relatório da onda em `docs/waves/onda-2.md`.

---

## Onda 3 — Humanização Semântica ✅

**Objetivo:** transformar textos em escrita mais natural, clara e autoral,
preservando significado e informações verificáveis.

### Escopo

- `humanizer/analysis.py` — análise: repetições, frases padronizadas,
  transições artificiais, coesão/coerência, vaguidão, redundância, voz
  passiva, excesso de conectivos.
- `humanizer/profiles.py` — 7 perfis: acadêmico científico, acadêmico
  acessível, profissional, institucional, narrativo, conversacional, autoral
  personalizado.
- `humanizer/intensity.py` — intensidade 0/25/50/75/100, tratada como
  **parâmetro de orientação**, não como percentual garantido de alteração.
- `humanizer/style_features.py` — extração de traços de estilo (formalidade,
  vocabulário, comprimento médio de frase, construção argumentativa,
  conectivos recorrentes, terminologia, organização de parágrafos, ritmo).
- `semantic_validator/` — extração de entidades, diff, validação.
- `api/v1/humanize.py` — `POST /api/v1/humanize`.

### Regras críticas

- Identificar e **mascarar** antes da chamada: valores numéricos, datas,
  nomes próprios, citações literais, referências, DOI, termos científicos,
  fórmulas, resultados, dados estatísticos, identificadores de tabela/figura.
- Após a revisão: comparar entidades e números, detectar omissões, verificar
  manutenção das citações, alertar sobre alteração de sentido.
- **Impedir aprovação automática** se houver perda de dado protegido.
- A LLM **não pode** inventar autores, artigos, DOI, resultados, estatísticas
  ou fontes bibliográficas.
- **Não** prometer evasão de detectores de IA.

### Critérios de aceite

- [x] As 7 perfis produzem sações visivelmente distintas sobre o mesmo texto.
- [x] A intensidade 0 não altera nada; 100 reescreve profundamente **sem**
      alterar entidades protegidas.
- [x] Teste garante que números, datas, DOI e citações literais sobrevêm
      intactos ao ciclo completo.
- [x] Teste garante que uma resposta de LLM que **omite** um número
      sinalizado gera alerta de severidade `critical`.
- [x] Teste garante que uma resposta que **altera** um número sinalizado
      gera alerta e reverte/registra a mudança.
- [x] Perfis autorais são construídos **apenas** com textos do próprio
      usuário (verificação por `owner_id`).
- [x] Testes usam *fake provider*; nenhuma chamada paga é feita.
- [x] `ruff check`, `ruff format --check`, `mypy`, `pytest` verdes;
      cobertura ≥ 80% em `app/services/humanizer/` e
      `app/services/semantic_validator/`.
- [x] Relatório da onda em `docs/waves/onda-3.md`.

---

## Onda 4 — Sistema de Templates ABNT ✅

**Objetivo:** desenvolver o motor de estruturação e formatação acadêmica.

### Escopo

- `templates/abnt/{general,articles,tcc,monographs,dissertations,theses,research_projects,reports}/`
- `templates/institutions/{ufms,ufgd}/` + schema de upload de perfil
  institucional.
- `app/services/academic/` — `structure.py`, `metadata.py`, `sections.py`,
  `numbering.py` (NBR 6024), `pagination.py`, `styles.py`.
- `api/v1/templates.py` — listagem, detalhe, resolução com perfil
  institucional, e registro de conflitos.

### Normas a aplicar (edições verificadas em 2026-10-21)

| Norma | Edição vigente | Uso no template |
|---|---|---|
| ABNT NBR 14724 | **2024** (com errata e versão corrigida) | Trabalhos acadêmicos — margens, paginação, estrutura |
| ABNT NBR 6023 | **2025** (3ª ed.) | Referências — Onda 5 |
| ABNT NBR 10520 | **2023** | Citações — Onda 5 |
| ABNT NBR 6024 | 2012 | Numeração progressiva das seções |
| ABNT NBR 6027 | 2012 | Sumário |
| ABNT NBR 6028 | 2021 | Resumo, resenha e recensão |
| ABNT NBR 6034 | 2004 | Índice remissivo |
| ABNT NBR 6022 | 2018 | Artigo científico |
| ABNT NBR 6029 | 2023 | Livros e folhetos (monografia) |
| ABNT NBR 10719 | **2025** | Relatório técnico/científico |
| ABNT NBR 15287 | **2025** (3ª ed.) | Projeto de pesquisa |

> ⚠️ Correções em relação ao enunciado original: **NBR 14725** trata de
> produtos químicos (não de monografias); **NBR 15287** é de projeto de
> pesquisa (relatório → NBR 10719); a **NBR 6023:2018** foi cancelada pela
> 6023:2025.

### Elementos estruturais

Capa · Folha de rosto · Folha de aprovação · Ficha catalográfica *(campo
reservado, nunca fictício)* · Dedicatória · Agradecimentos · Epígrafe ·
Resumo · Abstract · Palavras-chave · Lista de figuras · Lista de tabelas ·
Lista de abreviaturas · Lista de símbolos · Sumário · Introdução ·
Desenvolvimento · Conclusão · Referências · Glossário · Apêndices · Anexos ·
Índice remissivo *(opcional)*.

### Regras de página

A4 · margens configuráveis · impressão anverso/verso · margens distintas
para páginas pares e ímpares · estilos tipográficos · espaçamentos · recuos ·
alinhamento · quebras de seção · paginação · títulos hierárquicos · legendas
e fontes · citações longas · notas de rodapé · referências.

### Critérios de aceite

- [x] Os 8 tipos de template existem, são versionados e declaram suas fontes.
- [x] As margens da NBR 14724:2024 estão parametrizadas (anverso: 3/3/2/2 cm;
      verso: 3 cm à direita e superior, 2 cm à esquerda e inferior) e **não**
      estão hard-coded.
- [x] Um perfil institucional (UFMS/UFGD) sobrescreve apenas as regras que
      define, e o conflito com a norma geral é **registrado**, não ocultado.
- [x] Não há conformidade presumida com manual institucional: o relatório
      declara, por regra, a fonte e o grau de confiabilidade.
- [x] A ficha catalográfica é **reservada** (campo vazio), nunca preenchida
      com dados fictícios.
- [x] O sumário gerado é um **campo TOC real** do Word, não texto digitado.
- [x] `ruff check`, `ruff format --check`, `mypy`, `pytest` verdes;
      cobertura ≥ 80% em `app/services/academic/`.
- [x] Relatório da onda em `docs/waves/onda-4.md`.

---

## Onda 5 — Citações, Referências e Validador ABNT ✅

**Objetivo:** construir o módulo de integridade acadêmica.

### Escopo

- `references/models.py` — modelo de referência bibliográfica.
- `references/parser.py` — extração de entradas de referência do texto.
- `references/citation_parser.py` — citações autor-data e numérica, diretas
  e indiretas, longas.
- `references/matcher.py` — associação citação ↔ referência.
- `references/nbr6023.py` — formatação conforme NBR 6023:2025.
- `references/bibtex.py`, `references/csl_json.py` — importação.
- `references/doi.py` — identificação de DOI e consulta opt-in de metadados.
- `api/v1/academic.py` — validação + relatório.

### Requisitos

- Identificar referências ausentes (citada sem entrada) e não citadas
  (entrada sem citação).
- Detectar possíveis duplicações.
- Verificar campos bibliográficos obrigatórios.
- **Não inventar** metadados ausentes.
- Quando houver DOI, consultar serviço confiável e apresentar **alterações
  propostas para aprovação** — nunca aplicar automaticamente.
- Diferenciar: *erro comprovado* · *possível inconsistência* · *informação
  não verificável* · *recomendação institucional*.

### Critérios de aceite

- [x] Relatório de validação é auditável: cada achado tem **localização**,
      **severidade**, **categoria** e **ação sugerida**.
- [x] Citação correta é preservada; a associação citação↔referência é
      reportada com confiança.
- [x] Importação de BibTeX e CSL-JSON funciona e valida campos.
- [x] Metadados de DOI só são aplicados após aprovação explícita.
- [x] `ruff check`, `ruff format --check`, `mypy`, `pytest` verdes;
      cobertura ≥ 80% em `app/services/references/`.
- [x] Relatório da onda em `docs/waves/onda-5.md`.

---

## Onda 6 — Geração de Documentos

**Objetivo:** exportação acadêmica de qualidade.

### Escopo

- `document_export/docx_builder.py` — DOCX com **estilos nativos do Word**.
- `document_export/fields.py` — campos `TOC`, `PAGE`, `NUMPAGES`, `SEQ`,
  `STYLEREF`, `REF`.
- `document_export/pdf_builder.py` — PDF a partir do DOCX, em processo
  isolado.
- `document_export/writer.py` — TXT, Markdown.
- Histórico de versões + pré-visualização.
- `api/v1/exports.py`.

### Requisitos DOCX

Estilos nativos · títulos hierárquicos · campo de sumário automático ·
referências cruzadas quando possível · preservação de imagens e tabelas ·
gerência de quebras de página · cabeçalhos, rodapés e paginação ·
**nenhuma** simulação visual com espaços ou tabulações repetidas.

### Requisitos PDF

Renderizar a partir da estrutura do documento · validar tamanho de página e
margens · validar paginação · verificar quebras indevidas · comparar com o
DOCX de origem · **documentar diferenças e limitações** do renderizador.

### Critérios de aceite

- [ ] O DOCX abre no Word e mantém estilos reais (verificável por inspeção
      de `styles.xml` e `document.xml`).
- [ ] O sumário é um campo TOC real e atualiza no Word.
- [ ] Não há simulação de alinhamento por espaços/tabulações repetidas.
- [ ] O PDF, quando disponível, é comparado com o DOCX e as diferenças
      estão documentadas em `docs/architecture/PDF_RENDERER_NOTES.md`.
- [ ] Sem LibreOffice disponível, a limitação é declarada e apenas
      DOCX/TXT/Markdown são gerados.
- [ ] `ruff check`, `ruff format --check`, `mypy`, `pytest` verdes;
      cobertura ≥ 80% em `app/services/document_export/`.
- [ ] Relatório da onda em `docs/waves/onda-6.md`.

---

## Onda 7 — Interface e Experiência do Usuário

**Objetivo:** desenvolver uma experiência visual unificada.

### Páginas

1. Dashboard · 2. Editor · 3. Normalização · 4. Humanização semântica ·
5. Comparação de versões · 6. Templates ABNT · 7. Validador acadêmico ·
8. Histórico · 9. Perfis autorais · 10. Configurações de LLM ·
11. Exportação.

### Requisitos do editor

Comparação lado a lado · destaque de alterações · aceitar/rejeitar
sugestões · restaurar texto original · selecionar trechos específicos ·
aplicar formatação ao documento inteiro · acompanhar alertas acadêmicos ·
exibir custos estimados e consumo de tokens.

### Critérios de aceite

- [ ] Um usuário realiza o fluxo completo **sem** usar comandos técnicos.
- [ ] Testes Playwright cobrem o fluxo principal (colar → normalizar →
      selecionar provedor → humanizar → comparar → template → exportar).
- [ ] Nenhum segredo em `localStorage`/`sessionStorage` (verificado por
      teste automatizado).
- [ ] Interface responsiva e com componentes acessíveis (navegação por
      teclado, `aria-label`, contraste).
- [ ] Relatório da onda em `docs/waves/onda-7.md`.

---

## Onda 8 — Segurança, Testes e Estabilização

**Objetivo:** preparar uma versão estável.

### Escopo

- Autenticação e autorização · isolamento de dados por usuário · uploads
  seguros · limites de tamanho · validação de formato · sanitização de nome
  de arquivo · prevenção de path traversal · limites de consumo de API ·
  gestão e exclusão de chaves · política de retenção e exclusão de
  documentos · proteção contra prompt injection em documentos importados ·
  testes de integração · E2E · regressão ABNT · exportação · documentação de
  implantação.

### Critérios de aceite

- [ ] A suíte completa passa; nenhuma falha crítica conhecida.
- [ ] Cobertura global ≥ 80%.
- [ ] Revisão de segurança feita **e registrada** antes de qualquer
      disponibilização pública.
- [ ] `docs/DEPLOYMENT.md` cobre: variáveis de ambiente, migrações, proxy,
      TLS, backup, retenção e operação do renderizador de PDF.
- [ ] Relatório da onda em `docs/waves/onda-8.md`.

---

## 1. Requisitos funcionais e não funcionais

### 1.1 Funcionais

| ID | Requisito | Onda |
|---|---|---|
| RF-01 | Inserir texto, colar ou importar arquivo | 1 |
| RF-02 | Limpar e normalizar conteúdo sem LLM | 1 |
| RF-03 | Selecionar provedor de LLM e modelo | 2 |
| RF-04 | Informar chave de API própria (armazenada com segurança) | 2 |
| RF-05 | Escolher perfil de escrita | 3 |
| RF-06 | Configurar intensidade da revisão | 3 |
| RF-07 | Executar humanização semântica | 3 |
| RF-08 | Comparar versões; aceitar/rejeitar alterações | 3, 7 |
| RF-09 | Selecionar template acadêmico | 4 |
| RF-10 | Configurar dados de identificação | 4 |
| RF-11 | Aplicar formatação ABNT | 4 |
| RF-12 | Validar citações, referências e estrutura | 5 |
| RF-13 | Exportar DOCX e PDF (e TXT/Markdown) | 6 |
| RF-14 | Exibir estatísticas de normalização e custo estimado | 1, 2, 7 |
| RF-15 | Criar e reaproveitar perfis autorais | 3 |
| RF-16 | Consultar histórico de versões | 6, 7 |
| RF-17 | Gerar relatório de conformidade por regra | 5, 7 |

### 1.2 Não funcionais

| ID | Requisito | Como é verificado |
|---|---|---|
| RNF-01 | Normalização e formatação **não** exigem chave de LLM | Teste sem provedor configurado |
| RNF-02 | Determinismo: mesma entrada + mesma config → mesma saída | Teste de reprodutibilidade |
| RNF-03 | Documento original imutável | Teste de invariância do IR |
| RNF-04 | Rastreabilidade de toda transformação | Todo `rule_id` coberto por teste |
| RNF-05 | Segredos fora do repositório e dos logs | Teste automatizado de varredura |
| RNF-06 | Nenhuma invenção de referência ou resultado | Teste do validador semântico |
| RNF-07 | Cobertura ≥ 80% nas ondas 1–6 | `pytest --cov` no CI |
| RNF-08 | Tipagem estrita | `mypy --strict` sem erros |
| RNF-09 | Acessibilidade da interface | Auditoria + teste automatizado |
| RNF-10 | Documentação sempre atualizada | Checklist do Definition of Done |
| RNF-11 | I/O externa assíncrona; CPU-bound isolado | Revisão + teste de event loop |
| RNF-12 | Conformidade ABNT declarada por regra, com fonte | Formato do relatório de conformidade |

---

## 2. Riscos conhecidos

| ID | Risco | Impacto | Mitigação | Onda |
|---|---|---|---|---|
| R-01 | NFKC destrói superíndices/índices | **Alto** | NFKC desligado por padrão + exceções + regressão | 1 |
| R-02 | Remoção de emoji apaga `©`/`®`/`™` | Médio | Lista de exceção; regra só para emoji decorativos | 1 |
| R-03 | Setas químicas convertidas em `>` | **Alto** | Pseudográfico não toca `U+2190–U+21FF` | 1 |
| R-04 | Limpeza de Markdown come subscritos (`x_1`) | **Alto** | `norm.markdown` só fora de trecho protegido | 1 |
| R-05 | LLM altera números ou resultados | **Alto** | Máscara + validação semântica + bloqueio de aprovação | 3 |
| R-06 | LLM inventa referências | **Alto** | Prompt restritivo + validação de DOI/citação | 3, 5 |
| R-07 | Prompt injection via documento importado | **Alto** | Texto é conteúdo delimitado, nunca instrução | 2, 3 |
| R-08 | Vazamento de chave em log/resposta | **Alto** | `redact_secrets` + teste automatizado | 2 |
| R-09 | Manuais institucionais desatualizados (UFMS em 14724:2011) | Médio | Conflito registrado; norma vigente como referência | 4 |
| R-10 | PDF diverge do DOCX (LibreOffice) | Médio | Documentar limitações + comparador automático | 6 |
| R-11 | Sumário só aparece após atualizar campo no Word | Baixo | Tutorial no app + opção de pré-render | 6 |
| R-12 | Detecção de entidades protegidas é heurística | Médio | Reportar também o que não foi verificável | 3 |
| R-13 | Catalogação fictícia de referência | **Alto** | Campos obrigatórios verificados; sem fonte, fica vazio | 5 |
| R-14 | Custo de API descontrolado | Médio | Estimativa exibida + limites de requisição | 2, 8 |

Detalhamento em [`architecture/RISK_REGISTER.md`](architecture/RISK_REGISTER.md).

---

## 3. Pendências e ideias (não implementadas)

- Exportação para LaTeX (não solicitado; adicionar apenas com autorização).
- Detecção de plágio / similaridade (fora de escopo).
- Importação de documentos `.docx` como entrada (previsto na Onda 6).
- Painel de "conformidade" por instituição, com comparação automático entre
  duas versões do manual institucional.
- Suporte a outros idiomas no pipeline de humanização (o IR já é agnóstico).
- Indireção de chave de LLM por cofre externo (`*_API_KEY_ENV_NAME`): o
  `.env.example` foi limpo porque `Settings` não implementa essas variáveis;
  implementar na Onda 8 (segurança) ou mantê-las fora do escopo.

---

## 4. Formato do relatório de onda

Todo relatório em `docs/waves/onda-<N>.md` deve conter:

```markdown
# Onda N — <Nome>

## 1. Escopo executado
## 2. Funcionalidades concluídas
## 3. Arquivos criados ou modificados
## 4. Testes realizados
## 5. Resultados obtidos   (com saída real dos comandos)
## 6. Pendências
## 7. Riscos conhecidos
## 8. Próxima onda recomendada
## 9. Limitações declaradas
```

---

## 5. Critério de conclusão do projeto

O projeto será considerado funcional quando permitir:

1. Importar ou inserir um texto.
2. Executar normalização sem LLM.
3. Selecionar provedor e modelo de linguagem.
4. Humanizar semanticamente o texto.
5. Utilizar um perfil autoral.
6. Comparar o texto original ao revisado.
7. Selecionar um template ABNT.
8. Informar os metadados acadêmicos.
9. Gerar elementos pré-textuais.
10. Aplicar estilos e paginação.
11. Gerar sumário automático.
12. Validar citações e referências.
13. Exportar em DOCX e PDF.
14. Obter um relatório de conformidade e pendências.

> A conformidade ABNT será declarada **por regra validada**, com fonte e
> grau de confiabilidade — **nunca** presumida integralmente.
