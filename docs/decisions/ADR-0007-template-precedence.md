# ADR-0007 — Precedencia de regras: instituição > template > norma

- **Status**: Aceita
- **Data**: 2026-10-21
- **Impacto**: Alto

## Contexto

As fontes de regras de formatação se sobrepoem e, as vezes, conflitam:

1. **Norma geral ABNT** (NBR 14724:2024, 6023:2025, 10520:2023, 6024:2012,
   6027:2012, 6028:2021, 6034:2004, 6022:2018, 6029:2023, 10719:2025,
   15287:2025).
2. **Template do tipo de documento** (TCC, dissertação, artigo, relatório...),
   que já instância a norma para um caso concreto.
3. **Manual institucional** (UFMS, UFGD e outras), que pode exigir
   particularidades não previstas na norma.

Exemplo de conflito real já observado: o manual de trabalhos acadêmicos
disponível na biblioteca da UFMS ainda referência a **NBR 14724:2011** e a
**NBR 6023:2018**, ambas superadas (a 6023:2018 foi cancelada pela
6023:2025). Uma instituição pode, ainda assim, exigir o padrão antigo por
tradição, ou a propriá instituição pode estar desatualizada.

## Decisão

Adotar a precedencia:

```
instituicao  >  template do tipo de documento  >  norma geral ABNT
```

### Regras

1. **Resolução por herança.** Um perfil institucional declara apenas as
   regras que **substitui**; o restante vem do template, que por sua vez
   herda da base normativa.
2. **Conflito é registrado, nunca resolvido silenciosamente.** Cada
   substituição gera uma entrada em `TemplateResolved.conflicts` com:
   chave da regra, valor da norma, valor da instituição, fonte de cada um e
   data de consulta. O relatório de conformidade apresenta esses conflitos
   ao usuário.
3. **Norma nunca é reescrita.** Um perfil institucional só pode
   *desviar* de uma regra; o valor normativo permanece registrado e
   visível, com a marcação de desvio.
4. **Sem conformidade presumida.** Não se presume conformidade com o manual
   de uma universidade sem analisar o manual correspondente. A
   conformidade é declarada **por regra validada**, com fonte e grau de
   confiabilidade.
5. **Fontes datadas.** Toda regra carrega `norm`, `edition`, `section`,
   `url`, `consulted_at` e `confidence` (`high` | `medium` | `low`).

### Reconciliacao de fontes desactualizadas

Quando um manual institucional referência uma norma superada, o sistema:

- **não** aplica a regra antiga automaticamente;
- registra o conflito com a versão vigente da norma;
- sinaliza no relatório que a fonte institucional precisa de revisão
  (severidade `warning`, ação sugerida: "confirmar com a biblioteca").

## Consequências

### Positivas

- O usuário sabe exatamente qual regra produjo cada efeito.
- Conflitos institucionais ficam visíveis, em vez de virar surpresa na
  banca de defesa ou na revisão editorial.
- Templates institucionais podem ser escritos por cada universidade sem
  alterar o núcleo do sistema.

### Negativas

- O relatório de conformidade fica mais verboso (lista de conflitos).
- A resolução de herança exige um modelo de merge explícito
  (`TemplateResolved`), com trabalho adicional.

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|---|---|
| Norma > instituição | Ignora exigência legitima e local da instituição |
| Instituição > norma, sem registro | Perde rastreabilidade; erro institucional fica invisível |
| Resolver conflitos por "melhor palpite" | Não determinístico e não auditável |
| Hard-code de regras institucionais no código | Viola a regra "não codificar regra institucional como regra universal ABNT" |
