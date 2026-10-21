# ADR-0008 — Layout do repositório sem diretório externo de aninhamento

- **Status**: Aceita
- **Data**: 2026-10-21
- **Impacto**: Médio

## Contexto

A especificação do projeto apresenta a árvore sugerida com um diretório
externo:

```
humaniza-academico/
  backend/
  frontend/
  templates/
  docs/
  scripts/
  AGENTS.md
  README.md
  ...
```

O repositório de trabalho já **é** o projeto (`/home/renato.peixoto/projetos/humanizer`).
Criar um diretório `humaniza-academico/` dentro dele produziria um nível
extra de aninhamento sem ganho funcional, e a raiz do repositório git ficaria
com um único diretório.

## Decisão

Criar o conteúdo **na raiz do repositório**, sem o diretório externo de
aninhamento. Todos os demais diretórios e arquivos seguem a especificação
integralmente.

```
.
├── backend/  frontend/  templates/  docs/  scripts/
├── AGENTS.md  README.md  .env.example  .gitignore  docker-compose.yml
```

### Desvios menores, e sua justificativa

| Especificação | Realizado | Justificativa |
|---|---|---|
| `docs/architecture/`, `docs/standards/`, `docs/waves/`, `docs/decisions/` | Mantidos | Organization por tema, já previsto no mapa do `AGENTS.md` |
| `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/DECISIONS.md` | Mantidos | Exigidos explicitamente pela Onda 0 |
| `docs/decisions/` (pastas) + `docs/DECISIONS.md` | Ambos | O arquivo é o **índice**; a pasta guarda os ADRs individuais. Evita duplicar conteúdo |
| `backend/app/services/{...}` | Mantido | Estrutura exata da especificação |
| `backend/app/ir/` | **Adicionado** | Não existia na especificação. O IR é o contrato central do sistema (ver `ADR-0003`); o local `app/ir/` mantem a separação entre domínio e aplicação |
| `backend/app/core/` | Mantido | Config, logging, erros |
| `backend/alembic/` | Adicionado | Migrações de banco (ver `ADR-0011`) |

## Consequências

- A raiz do repositório tem conteúdo útil imediatamente.
- `docs/DECISIONS.md` e o índice navegável; `docs/decisions/` guarda o
  detalhe. A regra do `AGENTS.md` ("alterações neste arquivo exigem registro
  em `docs/DECISIONS.md`") permanece valida.
- Comandos de referência nos documentos são relativos a raiz do repositório.

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|---|---|
| Criar `humaniza-academico/` dentro do repositório | Aninhamento inútil; raiz do git com um único diretório |
| Achatar `docs/` (sem subpastas) | Perde a separação já documentada no `AGENTS.md` |
| Mover `docs/ARCHITECTURE.md` para `docs/architecture/` | Viola a exigência explicita da Onda 0 (tarefas 10-12) |
