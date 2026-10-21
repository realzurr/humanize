"""Perfis de normalização.

Um perfil é a **combinação de regras** que o motor executa. Ele existe para
que a interface ofereça escolhas com nome, e não uma lista de dezenas de
caixas de seleção.

O perfil tem três camadas:

1. o **catálogo** define a regra e seu padrão de ativação
   (:attr:`NormalizationRule.enabled_by_default`);
2. o **perfil** desliga regras inteiras por ``rule_id``;
3. as **opções** da requisição ligam ou desligam grupos de regras sem
   precisar conhecer os ``rule_id``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from app.services.normalizer.rules.base import RuleGroup

#: Opções oferecidas pela interface, na ordem em que aparecem.
OPTION_KEYS: tuple[str, ...] = ("nfkc", "invisiveis", "emojis", "markdown", "espacos")

#: Regras controladas por cada opção da interface.
OPTION_RULES: dict[str, tuple[str, ...]] = {
    "nfkc": ("norm.unicode.nfkc",),
    "invisiveis": (
        "norm.invisible.zwsp",
        "norm.invisible.bidi",
        "norm.invisible.soft_hyphen",
        "norm.invisible.variation",
        "norm.control.strip",
        "norm.ansi.strip",
    ),
    "emojis": ("norm.emoji.remove",),
    "markdown": (
        "norm.markdown.divider",
        "norm.markdown.heading",
        "norm.markdown.heading_empty",
        "norm.markdown.quote",
        "norm.markdown.bullet",
        "norm.markdown.emphasis",
        "norm.markdown.code",
        "norm.markdown.escape",
    ),
    "espacos": (
        "norm.whitespace.nbsp",
        "norm.punctuation.space_before",
        "norm.whitespace.collapse",
        "norm.whitespace.trailing",
        "norm.whitespace.blank_lines",
    ),
}

#: Opções ligadas por padrão.
DEFAULT_OPTIONS: dict[str, bool] = {
    "nfkc": False,
    "invisiveis": True,
    "emojis": True,
    "markdown": True,
    "espacos": True,
}


@dataclass(frozen=True, slots=True)
class NormalizationProfile:
    """Conjunto de regras habilitadas ou desabilitadas."""

    id: str = "padrao"
    """Identificador do perfil, ex.: ``padrao``."""

    description: str = "Perfil padrão: limpeza segura de texto acadêmico."
    """Descrição legível, exibida na interface."""

    disabled_rules: frozenset[str] = field(default_factory=frozenset)
    """Regras desligadas explicitamente por ``rule_id``."""

    enabled_rules: frozenset[str] = field(default_factory=frozenset)
    """Regras ligadas explicitamente, sobrepondo o padrão do catálogo."""

    def is_enabled(self, rule_id: str, *, default_enabled: bool) -> bool:
        """Indica se a regra deve ser aplicada.

        A precedência é: desligada explicitamente > ligada explicitamente >
        padrão do catálogo.
        """
        if rule_id in self.disabled_rules:
            return False
        if rule_id in self.enabled_rules:
            return True
        return default_enabled

    def with_options(self, options: dict[str, bool]) -> NormalizationProfile:
        """Devolve o perfil com as opções da interface aplicadas.

        Uma opção ligada/desligada sobrescreve o padrão do catálogo para as
        regras que ela controla. Opções desconhecidas são ignoradas.
        """
        desligadas = set(self.disabled_rules)
        ligadas = set(self.enabled_rules)
        for chave, valor in options.items():
            for rule_id in OPTION_RULES.get(chave, ()):
                if valor:
                    ligadas.add(rule_id)
                    desligadas.discard(rule_id)
                else:
                    desligadas.add(rule_id)
                    ligadas.discard(rule_id)
        return replace(
            self,
            disabled_rules=frozenset(desligadas),
            enabled_rules=frozenset(ligadas),
        )


#: Perfis disponíveis.
PROFILES: dict[str, NormalizationProfile] = {
    "padrao": NormalizationProfile(
        id="padrao",
        description="Perfil padrão: limpeza segura de texto acadêmico.",
    ),
    "conservador": NormalizationProfile(
        id="conservador",
        description="Perfil conservador: apenas caracteres invisíveis e espaços.",
        disabled_rules=frozenset(
            rule_id
            for chave, rule_ids in OPTION_RULES.items()
            if chave not in {"invisiveis", "espacos"}
            for rule_id in rule_ids
        )
        | frozenset({"norm.markdown.emphasis"}),
    ),
    "agressivo": NormalizationProfile(
        id="agressivo",
        description="Perfil agressivo: habilita também a normalização NFKC.",
        enabled_rules=frozenset({"norm.unicode.nfkc"}),
    ),
}


def get_profile(profile_id: str) -> NormalizationProfile:
    """Devolve o perfil pedido ou o perfil padrão, se o id for desconhecido."""
    return PROFILES.get(profile_id, PROFILES["padrao"])


def describe_profiles() -> list[dict[str, object]]:
    """Descrição serializável dos perfis disponíveis."""
    return [
        {
            "id": perfil.id,
            "description": perfil.description,
            "opcoes": list(OPTION_KEYS),
        }
        for perfil in PROFILES.values()
    ]


def describe_options() -> list[dict[str, object]]:
    """Descrição serializável das opções da interface."""
    return [
        {
            "chave": chave,
            "habilitada_por_padrao": DEFAULT_OPTIONS[chave],
            "regras": list(OPTION_RULES[chave]),
        }
        for chave in OPTION_KEYS
    ]


__all__ = [
    "DEFAULT_OPTIONS",
    "OPTION_KEYS",
    "OPTION_RULES",
    "PROFILES",
    "NormalizationProfile",
    "describe_options",
    "describe_profiles",
    "get_profile",
]


# Reexportado para conveniência dos consumidores do módulo.
GRUPOS: tuple[RuleGroup, ...] = tuple(RuleGroup)
