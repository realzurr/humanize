# ADR-0002 — Limites de módulo e direção de dependência

- **Status**: Aceita
- **Data**: 2026-10-21
- **Impacto**: Alto

## Contexto

O produto combina três naturezas de código com caracteristicas muito
diferentes: transformação de texto (determinística), interação com LLMs
(não determinística, com custo e latência) e formatação acadêmica (regra
documentada, versionada, sensível a direitos autorais).

O risco estrutural é a **contaminação cruzada**: um módulo de formatação que
importa um módulo de provider passa a depender de rede e de credenciais, e um
módulo de provider que conhece regras ABNT virá um emaranhado impossível de
manter.

## Decisão

Definir frontiers rigidas, com direção de dependência unidirecional:

```
api  ──►  services  ──►  ir
 │            │
 │            ▼
 └────────►  core  ◄──────  (transversal, sem dependencia de services)

repositories  ◄──  api / services   (acesso a dados)
providers     ◄──  services/humanizer
```

### Proibições explicitas

| # | Proibição | Motivo |
|---|---|---|
| P1 | `services/academic/**` não importa `services/providers/**` | Formatação não pode depender de rede, chave ou modelo |
| P2 | `services/providers/**` não importa `services/academic/**` | Provedores são genéricos; não conhecem ABNT |
| P3 | `services/normalizer/**` não importa `services/providers/**` | Normalização é garantidamente livre de LLM (ver `ADR-0006`) |
| P4 | `services/references/**` não importa `services/providers/**` | Validação bibliografica e determinística |
| P5 | Nenhuma regra de layout fora de `services/academic/**` e `templates/**` | A LLM nunca define layout (ver `ADR-0005`) |
| P6 | `services/**` não importa `api/**` | Dependência aponta para dentro |
| P7 | `core/**` não importa `services/**` ou `api/**` | Núcleo sem dependência de domínio |

### Contrato de serviço

Todo serviço público:

- recebe e devolve tipos do `ir` ou dos `schemas`;
- expoe métodos `async` para I/O externa e usa `asyncio.to_thread` ou
  subprocesso para trabalho CPU-bound (PDF, DOCX grande);
- sinaliza erros com `HumanizaError` (subclasses com `code` e `status_code`);
- não contem lógica de negócio na camada de API.

## Consequências

### Positivas

- Normalização e formatação são testáveis **sem** rede e **sem** chave.
- Trocar de provedor de LLM não toca a formatação.
- Testes de regressão ABNT são determinísticos e rápidos.
- A proibição P1/P3 é verificável mecanicamente (verificação a ser
  automatizada como teste de arquitetura na Onda 8).

### Negativas

- Algum compartilhamento precisa ser duplicado ou elevado a `ir`/`core`.
- Resolução de provider para humanização exige injeção de dependência.

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|---|---|
| Monolito único `app/services.py` | Escala mal, mistura responsabilidades, impossibilita testar sem LLM |
| Separar em microservicos | Complexidade operacional desproporcional ao problema; acoplamento por rede |
| Camada de serviço genérica (`BaseService`) com métodos dinâmicos | Perde a verificação de tipos do mypy estrito |
