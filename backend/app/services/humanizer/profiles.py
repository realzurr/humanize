"""Perfis autorais de humanização.

Sete perfis orientam a reescrita por LLM. Cada perfil carrega uma instrução de
sistema distinta e parâmetros de estilo. O perfil **autoral personalizado** é
construído **exclusivamente** a partir de textos do próprio usuário, com
verificação por ``owner_id`` (regra crítica da Onda 3).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuthorialProfile(BaseModel):
    """Perfil autoral de humanização."""

    model_config = ConfigDict(frozen=True)

    id: str
    nome: str
    descricao: str
    system_instruction: str
    """Instrução de sistema enviada ao provedor."""

    style: dict[str, Any] = Field(default_factory=dict)
    """Parâmetros de estilo (formalidade, vocabulário, ritmo...)."""

    owner_id: str | None = None
    """Dono dos textos de referência (só para o perfil autoral)."""

    base_texts: tuple[str, ...] = ()
    """Textos do próprio usuário que definem o estilo autoral."""

    @property
    def is_personalizado(self) -> bool:
        return self.owner_id is not None


PROFILES: dict[str, AuthorialProfile] = {
    "academico_cientifico": AuthorialProfile(
        id="academico_cientifico",
        nome="Acadêmico científico",
        descricao="Registro formal, impessoal e técnico, típico de artigos e teses.",
        system_instruction=(
            "Reescreva em registro acadêmico científico: formal, impessoal, preciso e "
            "técnico. Prefira voz ativa quando possível, sem coloquialismos. Preserve "
            "números, datas, citações e termos técnicos exatamente como estão."
        ),
        style={"formalidade": 1.0, "vocabulario": "técnico", "ritmo": "regular"},
    ),
    "academico_acessivel": AuthorialProfile(
        id="academico_acessivel",
        nome="Acadêmico acessível",
        descricao="Clareza e didática para público amplo, sem perder o rigor.",
        system_instruction=(
            "Reescreva em registro acadêmico acessível: claro, didático e direto, "
            "explicando termos complexos sem simplificar os resultados. Evite jargão "
            "desnecessário e frases longas."
        ),
        style={"formalidade": 0.7, "vocabulario": "comum", "ritmo": "variado"},
    ),
    "profissional": AuthorialProfile(
        id="profissional",
        nome="Profissional",
        descricao="Tom objetivo e executivo, adequado a relatórios e pareceres.",
        system_instruction=(
            "Reescreva em tom profissional e executivo: objetivo, conciso e orientado "
            "a conclusões. Frases curtas e vocabulário de negócios."
        ),
        style={"formalidade": 0.8, "vocabulario": "profissional", "ritmo": "regular"},
    ),
    "institucional": AuthorialProfile(
        id="institucional",
        nome="Institucional",
        descricao="Formal e impessoal, adequado a documentos oficiais e normativos.",
        system_instruction=(
            "Reescreva em registro institucional: formal, impessoal e normativo, com "
            "impessoalidade e tratamento cerimonioso, sem coloquialismo."
        ),
        style={"formalidade": 1.0, "vocabulario": "formal", "ritmo": "regular"},
    ),
    "narrativo": AuthorialProfile(
        id="narrativo",
        nome="Narrativo",
        descricao="Fluxo narrativo e coeso, sem perder a precisão factual.",
        system_instruction=(
            "Reescreva em estilo narrativo: fluxo envolvente e coeso, com transições "
            "naturais entre as ideias, mantendo os fatos e dados exatos."
        ),
        style={"formalidade": 0.5, "vocabulario": "comum", "ritmo": "variado"},
    ),
    "conversacional": AuthorialProfile(
        id="conversacional",
        nome="Conversacional",
        descricao="Linguagem próxima e natural, sem jargão.",
        system_instruction=(
            "Reescreva em tom conversacional e natural, como uma conversa clara com o "
            "leitor, sem gírias nem coloquialismos excessivos."
        ),
        style={"formalidade": 0.3, "vocabulario": "comum", "ritmo": "variado"},
    ),
}

#: Identificador do perfil autoral personalizado.
AUTORAL_ID = "autoral_personalizado"


def get_profile(profile_id: str) -> AuthorialProfile | None:
    """Devolve o perfil fixo ou ``None`` se não existir."""
    return PROFILES.get(profile_id)


def build_autoral_profile(
    owner_id: str,
    base_texts: tuple[str, ...],
    *,
    nome: str = "Autoral personalizado",
) -> AuthorialProfile:
    """Constrói o perfil autoral a partir de textos do próprio usuário.

    Regra crítica: o perfil autoral só pode ser construído com textos do
    próprio usuário, verificados por ``owner_id``.
    """
    if not owner_id.strip():
        raise ValueError("perfil autoral exige um owner_id")
    if not base_texts or not any(t.strip() for t in base_texts):
        raise ValueError("perfil autoral exige textos do próprio usuário")

    return AuthorialProfile(
        id=AUTORAL_ID,
        nome=nome,
        descricao="Estilo derivado exclusivamente dos textos do próprio autor.",
        system_instruction=(
            "Reescreva preservando o estilo autoral do usuário, derivado "
            "exclusivamente dos textos de referência fornecidos pelo próprio autor. "
            "Não introduza traços alheios ao autor e preserve números, datas, "
            "citações e termos técnicos."
        ),
        style={"formalidade": 0.6, "vocabulario": "autoral", "ritmo": "autoral"},
        owner_id=owner_id,
        base_texts=base_texts,
    )


def list_profiles() -> list[AuthorialProfile]:
    """Devolve os seis perfis fixos em ordem estável."""
    return [PROFILES[chave] for chave in PROFILES]
