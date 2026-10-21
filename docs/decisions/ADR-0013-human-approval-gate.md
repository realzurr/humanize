# ADR-0013 — Bloqueio de aprovação automática em perda de dado protegido

- **Status**: Aceita
- **Data**: 2026-10-21
- **Impacto**: Alto

## Contexto

A especificação da Onda 3 é explicita: "Impedir aprovação automática se
houver perda de dados protegidos" e "Permitir revisão humana de mudanças
substanciais".

A interface da Onda 7 preve aceitar/rejeitar sugestões individualmente. Se
cada sugestão pode ser aceita sem verificação, o usuário pode aprovar, sem
perceber, uma revisão que apagou um resultado numérico ou trocou um DOI.

## Decisão

Introduzir um **portão de aprovação** (`approval gate`) na transição entre a
revisão humana e a produção do documento.

### Regra

A aprovação automática (ou a aplicação em bloco de uma sugestão) é
**bloqueada** quando a validação semântica reporta:

| Achado | Severidade | Bloqueia? |
|---|---|---|
| Entidade `CRITICAL` ausente na revisão | `critical` | **Sim** |
| Entidade `CRITICAL` alterada | `critical` | **Sim** |
| Citação literal divergente | `critical` | **Sim** |
| Número presente na revisão e ausente no original | `high` | **Sim** (possível invenção de resultado) |
| Entidade `HIGH` ausente ou alterada | `high` | Não, mas exige confirmação explicita |
| Divergência de sentido detectada | `high` | Não, mas exige confirmação explicita |
| Mudança de estilo sem alteração factual | `info` | Não |

### Mecanismo

1. `semantic_validator` produz um `ValidationReport` com
   `ValidationFinding(severity, category, location, before, after, message,
   suggested_action)`.
2. A API expõe o relatório junto da sugestão.
3. O frontend destaca a sugestão bloqueada e exige ação explicita
   ("Aceitar mesmo assim" / "Rejeitar" / "Ver original").
4. A ação de "aceitar mesmo assim" é **registrada** no histórico da
   revisão, com o achado que foi sobreposto. Nada é descartado em silêncio.

### Rastreabilidade

Toda decisão de aprovação — automática, manual ou sobreposta — produz um
registro `Transformation` (ou `ValidationOverride`) na revisão, com autor
(quando houver), timestamp e o achado correspondente.

## Consequências

### Positivas

- O usuário não aprova, sem querer, a perda de um dado verificável.
- A decisão de sobrepor um alerta fica registrada e auditável.
- O relatório de conformidade pode declarar quantas divergências foram
  sobrepostas pelo autor.

### Negativas

- Há atrito no fluxo: um alerta legítimo pode exigir confirmação extra.
- Requer que o estado do achado (`blocked`/`overridden`/`resolved`) seja
  persistido junto da sugestão.

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|---|---|
| Apenas avisar, sem bloquear | O aviso é ignorado; o erro entra no documento final |
| Bloquear sempre que houver qualquer achado | Ruído excessivo; alertas de severidade `info` tornariam o sistema inutilizável |
| Reverter automaticamente a sugestão que quebra | Pode descartar uma reescrita legitima inteira |
| Confiar apenas no prompt do modelo | Não é confiável |
