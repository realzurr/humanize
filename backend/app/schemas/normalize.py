"""Schemas da API de normalização.

Os schemas ficam fora da camada de serviço: a API valida a entrada, converte
para o modelo de domínio e devolve a saída já serializável. Nenhuma regra de
normalização mora aqui.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

#: Limite de caracteres aceitos em uma requisição de normalização.
MAX_TEXT_LENGTH = 1_000_000

#: Limite de ``rule_id`` que podem ser desligados manualmente.
MAX_DISABLED_RULES = 60


class NormalizeRequest(BaseModel):
    """Requisição de normalização."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    texto: str = Field(
        default="",
        max_length=MAX_TEXT_LENGTH,
        description="Texto a normalizar.",
    )

    perfil: str = Field(
        default="padrao",
        max_length=40,
        description="Identificador do perfil de normalização.",
    )

    opcoes: dict[str, bool] = Field(
        default_factory=dict,
        description="Opções por grupo de regras (nfkc, invisiveis, emojis, markdown, espacos).",
    )

    regras_desativadas: list[str] = Field(
        default_factory=list,
        max_length=MAX_DISABLED_RULES,
        description="Identificadores de regras a desligar manualmente.",
    )


class TransformacaoOut(BaseModel):
    """Transformação aplicada, resumida por regra."""

    model_config = ConfigDict(frozen=True)

    stage: str = "normalize"
    rule_id: str
    description: str = ""
    category: str = "geral"
    count: int = Field(ge=0)
    severity: str = "info"
    before: str = ""
    after: str = ""


class EntidadeProtegidaOut(BaseModel):
    """Entidade protegida detectada no texto."""

    model_config = ConfigDict(frozen=True)

    id: str
    kind: str
    text: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    level: str = "medium"
    fingerprint: str = ""


class NormalizeResponse(BaseModel):
    """Resposta da normalização."""

    model_config = ConfigDict(frozen=True)

    texto: str = Field(description="Texto normalizado.")
    transformacoes: list[TransformacaoOut] = Field(default_factory=list)
    total_caracteres_antes: int = Field(ge=0)
    total_caracteres_depois: int = Field(ge=0)
    entidades_protegidas: list[EntidadeProtegidaOut] = Field(default_factory=list)
    regras_desativadas: list[str] = Field(default_factory=list)
    avisos: list[str] = Field(default_factory=list)
