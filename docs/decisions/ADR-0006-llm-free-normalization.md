# ADR-0006 — Normalização e livre de LLM e baseada em regras configuráveis

- **Status**: Aceita
- **Data**: 2026-10-21
- **Impacto**: Alto

## Contexto

A Onda 1 implementa a limpeza de texto. A especificação é explicita: "a
normalização e a formatação não poderão exigir uma chave de LLM".

Um normalizador baseado em LLM traria três problemas: custo e latência por
texto, não-determinismo (a mesma entrada produz saidas diferentes) e risco de
alterar conteúdo verificável. Além disso, tarefas como remover um caractere
zero-width ou decodificar uma entidade HTML são **deterministas por natureza**;
usar um modelo para isso seria desperdício e risco.

## Decisão

O motor de normalização é uma **cadeia de regras puras**, cada uma isolada:

```python
class NormalizationRule(abc.ABC):
    rule_id: str                  # "norm.invisible.zwsp" — chave estavel
    description: str
    category: str
    configurable: bool
    enabled_by_default: bool
    touches_protected_content: bool

    def apply(self, text: str) -> RuleResult: ...
```

### Caracteristicas obrigatorias

1. **Identificador estável** — `rule_id` é a chave usada em configuração,
   métricas, relatórios e testes. Não muda entre versões.
2. **Configurável** — cada regra pode ser ligada/desligada pelo usuário.
3. **Testável isoladamente** — uma regra, um teste, um caso "não faz nada"
   quando desabilitada.
4. **Sem acesso a trecho protegido** — o motor segmenta o texto em trechos
   protegidos e livres, e aplica a regra **apenas** nos livres, salvo
   declaração explicita `touches_protected_content = True` (que exige
   aprovação e gera alerta).
5. **Reportavel** — cada aplicação gera um `RuleOccurrence` com contagem,
   amostra antes/depois e posições.

### Motor

`app/services/normalizer/engine.py` compoe as regras em um pipeline
determinístico e produz um `NormalizationReport` com o total por regra e por
categoria, além das entidades protegidas detectadas.

### Riscos herdados do repositório de referência (a evitar)

| Risco | Mitigação adotada |
|---|---|
| NFKC converte `10⁻⁶` -> `10-6` | `norm.unicode.nfkc` **desligada por padrão** ou com lista de exceções; regressão com `10⁻⁶`, `x²`, `Na⁺`, `CO₂` |
| Remocao de emoji apaga `©`, `®`, `™` | Lista de exceção; remoção apenas de pictogramas decorativos |
| Setas quimicas (`U+2192`) viram `>` | Regra de pseudográfico **não** alcanca `U+2190–U+21FF` |
| Limpeza de Markdown come subíndice (`x_1`) | `norm.markdown` só fora de trecho protegido; regex exige delimitador não alfanumérico |
| Hífen opcional (`U+00AD`) removido dentro de palavra | Detecção de posição: hífen no meio de palavra e sinalizado, não removido silenciosamente |

## Consequências

### Positivas

- Normalização funciona offline, sem chave, sem custo e sem latência.
- Resultado idêntico em qualquer máquina e qualquer execução.
- Cada regra pode ser medida, revertida e auditada.
- O usuário ve exatamente o que mudou e por que.

### Negativas

- Heuristicas exigem calibragem manual (a Onda 1 inclui suíte de regressão
  documental justamente para isso).
- Casos muito específicos podem exigir uma regra nova — processo lento, mas
  explícito e auditável.

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|---|---|
| LLM para "limpar" o texto | Não determinístico, caro, lento, e capaz de alterar conteúdo |
| Um único regex gigante | Impossivel de medir, desabilitar por categoria ou testar isoladamente |
| `unidecode`/transliteração completa | Destroi acentos, grego e símbolos científicos — inaceitável em texto acadêmico |
| Biblioteca pronta de saneamento | Nenhuma cobre o conjunto de requisitos (preservação acadêmica + configurabilidade por regra) |
