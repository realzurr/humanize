# ADR-0010 — Toolchain Python 3.12 com uv, ruff, mypy estrito e pytest

- **Status**: Aceita
- **Data**: 2026-10-21
- **Impacto**: Médio

## Contexto

O produto exige Python 3.12+ (sintaxe moderna, `type` nativo, melhor suporte
a `asyncio` e `ExceptionGroup`). O ambiente de desenvolvimento é Ubuntu
20.04, com Python 3.8/3.9 do sistema — insuficiente.

## Decisão

| Ferramenta | Escolha | Versão / Observação |
|---|---|---|
| Interpretador | CPython | **3.12** (gerenciado pelo `uv`) |
| Gestão de ambiente/dependências | `uv` | `uv venv` + `uv pip install -e ".[dev]"` |
| Lint + formatação | `ruff` | `line-length = 100`, `target-version = "py312"` |
| Tipagem | `mypy` | modo **`strict`**, plugin `pydantic.mypy` |
| Testes | `pytest` + `pytest-asyncio` | `asyncio_mode = "auto"` |
| Cobertura | `pytest-cov` | limiar de 80% nas ondas 1-6 |
| Servidor | `uvicorn[standard]` | com reload em desenvolvimento |
| Validação de schema | `pydantic v2` | `frozen=True` nos fatos imutaveis |
| ORM | `SQLAlchemy 2.0` | ver `ADR-0011` |
| Migrações | `Alembic` | ver `ADR-0011` |

### Regras de configuração

- `ruff` seleciona `E, W, F, I, N, UP, B, C4, SIM, ANN, ASYNC, S, RUF`.
- `ANN401` (`Any` em assinatura) e ignorado **apenas** em schemas de API,
  com justificativa.
- `S105`/`S106` (segredos em código) são ignorados **apenas** em
  `app/core/config.py` (que le chaves de ambiente) e em testes.
- `RUF001/002/003` (caracteres Unicode ambíguos) são ignorados: o projeto
  trata **deliberadamente** de caracteres de largura variável, sinais
  matemáticos e dashes.
- `filterwarnings = ["error"]` — avisos de biblioteca viram erro.

### Comandos de verificação (obrigatórios antes de qualquer entrega)

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

## Consequências

### Positivas

- Reprodutibilidade: `uv` fixa o interpretador e as dependências.
- `mypy --strict` impede que a tipagem se degrade ao longo das ondas.
- `filterwarnings = ["error"]` evita que depreciações passem despercebidas
  (foi assim que se detectou, já na Onda 0, que o `TestClient` do Starlette
  passava a exigir `httpx2`).
- Instalação em segundos, sem `pip install` global.

### Negativas

- `uv` é uma dependência extra em relação a `pip` (mitigada: é uma
  ferramenta da Astral, largementemente adotada).
- `mypy --strict` exige disciplina de tipagem; todo `Any` precisa de
  justificativa.

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|---|---|
| Python 3.8/3.9 do sistema | Versão miníma não atendida pelo projeto |
| Poetry | Mais lento que `uv`; resolução de conflito mais complexa |
| `pip` + `venv` + `requirements.txt` | Funciona, mas sem travamento de versão e mais lento |
| `pyright` | Mais rápido, mas `mypy --strict` é o padrão adotado no `AGENTS.md` |
