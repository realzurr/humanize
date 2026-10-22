# Onda 7 — Interface e Experiência do Usuário

- **Data**: 2026-10-22
- **Escopo**: experiência visual unificada com as 11 páginas da SPA
  (React 18 + TypeScript + Vite + Tailwind), editor comparativo lado a lado
  com aceitação/rejeição por trecho, cliente de API completo e testes
  unitários (Vitest) e E2E (Playwright), incluindo a verificação automatizada
  de ausência de segredos no navegador.
- **Status**: concluída.

---

## 1. Escopo executado

| # | Entregável do ROADMAP | Onde | Estado |
|---|---|---|---|
| 1 | 11 páginas unificadas | `frontend/src/pages/` | ✅ |
| 2 | Editor comparativo (aceitar/rejeitar, restaurar) | `frontend/src/components/RevisorDiff.tsx`, `utils/revisao.ts` | ✅ |
| 3 | Cliente da API e tipos espelhando os schemas | `frontend/src/services/api.ts`, `frontend/src/types/index.ts` | ✅ |
| 4 | Estado compartilhado do documento | `frontend/src/context/DocumentoContext.tsx` | ✅ |
| 5 | Testes unitários (Vitest) | `frontend/tests/unit/` | ✅ |
| 6 | Testes E2E do fluxo principal (Playwright) | `frontend/tests/e2e/fluxo.spec.ts` | ✅ |
| 7 | Verificação de ausência de segredos no navegador | `frontend/tests/e2e/fluxo.spec.ts` | ✅ |
| 8 | Infra de qualidade do frontend (ESLint/Vitest/Playwright) | `eslint.config.js`, `vitest.config.ts`, `playwright.config.ts` | ✅ |

## 2. Funcionalidades concluídas

- **11 páginas** ligadas por navegação lateral responsiva (`App.tsx` +
  `constants/navegacao.ts`): Dashboard, Editor, Normalização, Humanização,
  Comparação, Templates ABNT, Validador, Histórico, Perfis autorais,
  Configurações de LLM e Exportação.
- **Estado compartilhado em memória** (`DocumentoContext`): o documento flui
  entre as telas (original → normalizado → humanizado → final), permitindo o
  ciclo completo sem comandos técnicos e sem persistência (esta pertence à
  Onda 8).
- **Editor comparativo** (`RevisorDiff`): diff por palavra com agrupamento de
  alterações em sugestões revisáveis (`utils/revisao.ts`), aceitar/rejeitar por
  trecho, aceitar/rejeitar todas, restaurar o original e composição do texto
  final sincronizada com o contexto.
- **Humanização**: seleção de perfil (7 perfis), intensidade discreta
  (0/25/50/75/100), provedor/modelo, perfil autoral com `owner_id` e textos do
  próprio autor, e exibição de análise estilística, validação semântica
  (achados com severidade) e consumo de tokens/custo.
- **Configurações de LLM**: registro/remoção de chave (input `type=password`,
  `autoComplete=off`), indicadores `configured`/`last4` e listagem de modelos —
  nenhum segredo gravado ou devolvido ao navegador.
- **Templates/Validador/Exportação/Histórico**: resolução com conflitos
  institucionais visíveis, relatório auditável de citações/referências,
  metadados + formatos + pré-visualização, e download dos artefatos exportados.
- **Acessibilidade**: navegação por teclado (elementos nativos `button`/`select`/
  `textarea`), `aria-label`/`aria-labelledby`/`aria-live`, foco visível e
  contraste (paleta WCAG AA em `tailwind.config.js`).

## 3. Arquivos criados ou modificados

- **Criados (frontend)**:
  `eslint.config.js`, `vitest.config.ts`, `playwright.config.ts`,
  `src/test/setup.ts`, `src/constants/{perfis,navegacao}.ts`,
  `src/context/DocumentoContext.tsx`, `src/components/RevisorDiff.tsx`,
  `src/utils/{revisao,severidade}.ts`,
  `src/pages/{Dashboard,Editor,Humanizacao,Comparacao,Templates,Validador,Historico,Perfis,Llm,Exportacao}.tsx`,
  `tests/unit/{diff,revisao,severidade}.test.ts`,
  `tests/unit/RevisorDiff.test.tsx`, `tests/e2e/fluxo.spec.ts`.
- **Modificados (frontend)**:
  `src/App.tsx`, `src/main.tsx`, `src/services/api.ts`, `src/types/index.ts`,
  `src/pages/Normalizacao.tsx`, `tsconfig.json`, `package.json`,
  `package-lock.json`.
- **Documentação**:
  `docs/ROADMAP.md` (estado e critérios da Onda 7), `docs/ARCHITECTURE.md`
  (§9), `README.md` (estado, tabela de ondas e badge de testes),
  `docs/waves/onda-7.md`.

### Dependências adicionadas/ajustadas (justificativa)

| Pacote | Ação | Justificativa |
|---|---|---|
| `typescript-eslint`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh` | adicionados (dev) | habilitar o `eslint` já previsto no `package.json` |
| `vitest` 2.1 → 3.2 | atualizado | compatibilidade com Vite 6 (o 2.x usa Vite 5) |
| `@playwright/test` 1.64 → 1.61 | rebaixado | 1.64 (chromium 1248) não suporta Ubuntu 20.04; 1.61 (chromium 1228) já instalado e funcional |

## 4. Testes realizados

| Suíte | Testes |
|---|---|
| Unitários — `utils/diff` | 4 |
| Unitários — `utils/revisao` (agrupamento + composição) | 4 |
| Unitários — `utils/severidade` | 4 |
| Unitários — componente `RevisorDiff` | 2 |
| E2E — fluxo principal + ausência de segredos | 1 |
| Subtotal Onda 7 (frontend) | **15** |
| Backend (ondas 0–6, inalterado) | 423 |
| **Total** | **438** |

## 5. Resultados obtidos (com saída real dos comandos)

Backend (sem regressões):

```
$ ruff check .
All checks passed!

$ ruff format --check .
143 files already formatted

$ mypy
Success: no issues found in 92 source files

$ pytest
423 passed
```

Frontend:

```
$ npm run lint        # eslint src tests --max-warnings 0
(limpo)

$ npm run typecheck   # tsc --noEmit
(limpo)

$ npm run build
✓ 51 modules transformed · built in 2.11s

$ npm run test        # vitest run
Test Files  4 passed (4)
     Tests  14 passed (14)

$ npx playwright test
1 passed (5.1s)
```

## 6. Pendências

| Pendência | Onda | Observação |
|---|---|---|
| Persistência relacional do documento (SQLAlchemy/Alembic) com isolamento `owner_id` | 8 | Hoje o documento vive em memória no cliente |
| Autenticação/upload seguro/limites de API | 8 | Interface já não grava segredos |
| Rota de listagem de perfis autorais no backend | 8 (ou adiante) | Hoje a lista é espelhada no frontend (`constants/perfis.ts`) |

## 7. Riscos conhecidos

- **Segredos no navegador (mitigado)**: a chave é enviada ao backend e a API
  só devolve indicadores; o teste E2E verifica a ausência de segredos em
  `localStorage`/`sessionStorage`.
- **E2E com API mockada**: o fluxo é exercitado com `page.route`, sem chamadas
  reais a LLM (conforme regra permanente de não fazer chamadas pagas em
  desenvolvimento/teste). A integração real backend↔frontend segue coberta
  pelos testes de integração Python (`TestClient`).
- **Playwright × Ubuntu 20.04**: versão pinada em 1.61.0 (chromium 1228),
  pois o chromium 1248 das versões recentes não é suportado nesta plataforma
  EOL. Em CI moderno, o pin pode ser elevado.
- **Estado em memória**: recarregar a página perde o documento não exportado;
  comportamento esperado até a persistência da Onda 8.

## 8. Próxima onda recomendada

**Onda 8 — Segurança, Testes e Estabilização**: autenticação e autorização,
isolamento de dados por usuário, uploads seguros, limites de tamanho/consumo,
política de retenção, proteção contra prompt injection em documentos
importados, testes de integração/E2E/regressão ABNT e `docs/DEPLOYMENT.md`.
**Não iniciar sem autorização expressa.**

## 9. Limitações declaradas

1. **Sem persistência multiusuário**: o documento e o histórico de exportações
   usam, respectivamente, estado em memória no cliente e o `ExportHistoryStore`
   em disco do backend; a camada relacional com `owner_id` pertence à Onda 8.
2. **Perfis autorais sem rota de listagem**: a lista dos 7 perfis é mantida no
   frontend e espelha `app/services/humanizer/profiles.py`; uma rota dedicada
   seria um refinamento futuro.
3. **E2E usa mock de API**: a ausência de chamadas pagas a LLM em testes é uma
   regra permanente; portanto o E2E valida a interface contra respostas
   controladas, e não a integração com provedores reais.
4. **Pino de Playwright**: `@playwright/test@1.61.0` para compatibilidade com
   o ambiente Ubuntu 20.04 de desenvolvimento.
