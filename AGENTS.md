# AGENTS.md — Regras Permanentes de Desenvolvimento

> **Este arquivo é binding.** Ele se aplica a **todos** os agentes, humanos e
> ferramentas que operem neste repositório, em **todas** as ondas, inclusive
> após a Onda 0. Alterações neste arquivo exigem registro em
> `docs/DECISIONS.md`.

---

## 1. Idioma

- Código, identificadores, nomes de arquivo e mensagens de commit em
  **português do Brasil** ou em inglês técnico consistente com o que já
  existe no arquivo tocado. **Não** misturar idiomas no mesmo símbolo.
- Docstrings, comentários e documentação de interface em **pt-BR**.
- Identificadores Python em `snake_case`; classes em `PascalCase`;
  constantes em `SCREAMING_SNAKE_CASE`. Frontend em `camelCase` para
  variáveis e `PascalCase` para componentes.
- Comentários explicam **por quê**, não **o quê**. O código deve ser
  autoexplicativo; comentário redundante é ruído.

---

## 2. Fluxo de trabalho por ondas

1. **Ler** `AGENTS.md`, `docs/ROADMAP.md`, `docs/DECISIONS.md` e o relatório da
   onda anterior em `docs/waves/`.
2. **Analisar** o estado real do repositório (`git status`, `git diff`) e
   executar a suíte de testes antes de modificar qualquer coisa.
3. **Definir** tarefas objetivas antes de codificar.
4. **Implementar** **somente** o escopo da onda autorizada. Nada além.
5. **Testar**: toda regra de transformação, todo endpoint e todo componente
   novo têm teste.
6. **Corrigir** os erros identificados (incluindo os do lint e do type check).
7. **Documentar**: atualizar `docs/`, templates e comentários.
8. **Relatório** final no formato definido em `docs/ROADMAP.md`.
9. **Parar** e aguardar autorização expressa para a próxima onda.

> **Regra dura:** não iniciar a onda seguinte sem autorização explícita do
> responsável pelo projeto. "Continue" sem nomear a onda **não** é autorização
> para avançar.

---

## 3. Regras de engenharia (obrigatórias)

1. **Código limpo e modular.** Funções pequenas, nomes explícitos, SRP.
2. **Sem acoplamento entre LLM e formatação ABNT.** Nenhuma camada de
   formatação pode importar um módulo de provider, e vice-versa.
3. **A LLM nunca define layout.** Margens, paginação, numeração, estilos e
   quebras de seção são sempre determinísticos e vêm de template.
4. **O documento original é imutável.** Toda transformação produz uma nova
   revisão; `original_text` nunca é sobrescrito.
5. **Representação intermediária estruturada.** Nenhuma etapa opera sobre
   texto solto fora do IR (`app/ir/`).
6. **Rastreabilidade.** Toda transformação relevante gera um registro
   `Transformation` com `rule_id`, contagem e localização.
7. **Testes para cada módulo.** Cobertura mínima de 80% nas ondas 1–6.
8. **Segredos fora do repositório.** Nenhuma chave em código, fixtures,
   `.env` versionado ou log.
9. **Não inventar referências.** Autores, artigos, DOI, resultados,
   estatísticas e fontes bibliográficas nunca são inventados.
10. **Não suprimir informação científica.**
11. **Números e resultados só mudam com sinalização explícita** e aprovação
    do usuário.
12. **Preservar** tabelas, equações, código e citações literais.
13. **Decisões de arquitetura são registradas** em `docs/decisions/`.
14. **Documentação sempre atualizada** junto com a mudança de código.
15. **Qualidade mínima antes de entregar:** `ruff check`, `ruff format --check`,
    `mypy`, `pytest` — todos sem erros.

---

## 4. Segurança (aplicável desde já)

- **Nunca** registrar, imprimir ou serializar chaves de API. O filtro
  `redact_secrets` (`app/core/logging.py`) é obrigatório para novos logs.
- **Nunca** devolver credenciais ao frontend após armazená-las. A API expõe
  apenas *indicadores* (`configured: bool`, `last4`).
- **Nunca** usar `localStorage`/`sessionStorage` para segredos no frontend.
- Credenciais persistidas (multiusuário) usam criptografia autenticada
  (AES-GCM via `cryptography`), com chave fora do banco.
- Validação de entrada em toda a borda: Pydantic com limites estritos.
- Uploads: limite de tamanho, validação de tipo real (magic bytes), nome de
  arquivo sanitizado, ausência de path traversal.
- Imports de documento são tratados como **entrada não confiável**: o texto
  importado é conteúdo, nunca instrução (proteção contra prompt injection).
- Consultas externas (DOI/Crossref) são **opt-in** e nunca enviam o documento.

---

## 5. Conformidade ABNT

- Toda regra de formatação é **parametrizada** e acompanhada da sua fonte
  (norma + edição + URL + data de consulta).
- **Não** codificar regra institucional específica como regra universal ABNT.
- **Precedência** (ver `ADR-0007`): `instituição > template do tipo de
  documento > norma geral ABNT`. Conflitos são **registrados**, não
  resolvidos silenciosamente.
- **Não** reproduzir texto integral de norma protegida por direitos
  autorais. Resumir estrutura e regras.
- **Não** gerar ficha catalográfica fictícia — reservar o campo.
- **Não** declarar conformidade integral. O relatório declara conformidade
  **por regra validada**, com fonte e grau de confiabilidade.

---

## 6. Qualidade de código

- **Ruff**: lint e formatação. `line-length = 100`, `target-version = py312`.
- **Mypy**: modo `strict`. Tipos explícitos em todas as assinaturas públicas.
  `Any` só é aceito em schemas de API, com justificativa.
- **Pydantic v2**: validação em toda a borda da API. Modelos `frozen=True`
  quando o objeto representa um fato imutável.
- **SQLAlchemy 2.0**: estilo `Mapped[]` / `mapped_column`. Migrações via
  Alembic — nunca `create_all` em produção.
- **FastAPI**: rotas em `app/api/v1/`, prefixo `/api/v1`. Schemas Pydantic
  separados da camada ORM. Erros de domínio via `HumanizaError`.
- **Testes**: `pytest`, `pytest-asyncio` (`asyncio_mode = "auto"`).
  Testes de regressão documental usam textos-fixture versionados.
- **Async**: toda I/O externa (rede, disco lento, LLM) é `async`. O
  renderizador de PDF roda em processo isolado (`asyncio.to_thread` ou
  subprocesso), nunca no event loop.
- **Comentários**: proíbido comentar código óbvio. Docstrings em português,
  explicando intenção e restrições.

---

## 7. Dependências

- Adicionar dependência nova exige: (a) justificativa no relatório da onda;
  (b) `pyproject.toml` atualizado; (c) verificação de licença compatível.
- Preferir bibliotecas **mantidas**. Evitar dependências com licença copyleft
  forte (GPL/AGPL) no `backend/` — ver `ADR-0001`.
- `requirements.txt`/`uv.lock` são gerados; não editar à mão.

---

## 8. Commits e Git

- Não commitar sem pedido explícito.
- Antes de commitar: `git status`, `git diff`, `git log --oneline -10`.
- Commitar **apenas** arquivos intencionais. Nunca segredos, `.env`, dados
  de teste reais, artefatos de build ou `node_modules`.
- Mensagem em português, no formato:
  `onda<N>: <descrição curta>` (ex.: `onda1: adiciona motor de normalização`).
- Nunca reescrever histórico já publicado (`force-push` só com autorização).

---

## 9. O que **não** fazer

- Não instalar, publicar ou modificar serviços em servidores externos.
- Não fazer chamadas a LLMs pagos durante desenvolvimento ou testes.
  Testes usam *fake providers*; chamadas reais só mediante autorização
  explícita e com orçamento definido.
- Não implementar etapas fora da onda autorizada.
- Não "melhorar" escopo unilateralmente. Registrar a ideia em
  `docs/ROADMAP.md` → "Pendências / Ideias".
- Não afirmar sucesso sem executar o comando de verificação correspondente.
- Não esconder falhas: se algo não puder ser feito, **declarar a limitação**.

---

## 10. Definição de pronto (Definition of Done)

Uma tarefa só está pronta quando:

1. o código está implementado dentro do escopo autorizado;
2. `ruff check`, `ruff format --check`, `mypy` e `pytest` passam;
3. há teste cobrindo o comportamento novo (unitário ou de integração);
4. a documentação foi atualizada (README, ARCHITECTURE, ROADMAP, DECISIONS);
5. o relatório da onda foi gerado com o formato exigido;
6. as limitações e pendências estão declaradas.

---

## 11. Mapa rápido dos arquivos de regras

| Preciso de… | Onde está |
|---|---|
| Arquitetura e fluxo de dados | `docs/ARCHITECTURE.md` |
| O que fazer em cada onda | `docs/ROADMAP.md` |
| Por que as coisas são como são | `docs/DECISIONS.md` + `docs/decisions/` |
| Regras das normas ABNT e fontes | `docs/standards/ABNT_NORMS_RESEARCH.md` |
| Riscos conhecidos | `docs/architecture/RISK_REGISTER.md` |
| Relatório da última onda | `docs/waves/` |
| Regras ABNT parametrizáveis | `templates/` |
