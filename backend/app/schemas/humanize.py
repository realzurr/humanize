"""Schemas da API de humanização.

A requisição carrega o texto, o perfil, a intensidade e o provedor/modelo. O
perfil **autoral personalizado** exige ``owner_id`` e ``textos_autorais``
(textos do próprio usuário), verificados no serviço.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.services.humanizer.analysis import AnalysisReport
from app.services.humanizer.style_features import StyleFeatures

MAX_TEXT_LENGTH = 1_000_000
MAX_AUTORAL_TEXTS = 20
MAX_AUTORAL_TEXT_LENGTH = 50_000


class HumanizeRequest(BaseModel):
    """Requisição de humanização."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    texto: str = Field(default="", max_length=MAX_TEXT_LENGTH)
    perfil: str = Field(default="academico_cientifico", max_length=40)
    intensidade: int = Field(default=50, ge=0, le=100)
    provedor: str = Field(default="openai", max_length=40)
    modelo: str = Field(default="", max_length=100)
    owner_id: str | None = Field(default=None, max_length=100)
    textos_autorais: list[str] = Field(default_factory=list, max_length=MAX_AUTORAL_TEXTS)


class AchadoOut(BaseModel):
    """Achado de validação semântica."""

    model_config = ConfigDict(frozen=True)

    severidade: str
    categoria: str
    entidade_id: str = ""
    tipo: str = ""
    nivel: str = ""
    antes: str = ""
    depois: str = ""
    mensagem: str = ""
    acao_sugerida: str = ""


class ValidacaoOut(BaseModel):
    """Relatório de validação semântica."""

    model_config = ConfigDict(frozen=True)

    achados: list[AchadoOut] = Field(default_factory=list)
    entidades_antes: int = 0
    entidades_depois: int = 0
    perdas: int = 0
    alteracoes: int = 0
    invencoes: int = 0
    bloqueado: bool = False


class UsoOut(BaseModel):
    """Consumo de tokens e custo estimado."""

    model_config = ConfigDict(frozen=True)

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    custo_estimado_usd: float = 0.0


class HumanizeResponse(BaseModel):
    """Resposta da humanização."""

    model_config = ConfigDict(frozen=True)

    texto: str
    perfil: str
    intensidade: int
    modelo: str = ""
    provedor: str = ""
    bloqueado: bool = False
    analise: AnalysisReport = AnalysisReport()
    estilo: StyleFeatures = StyleFeatures(formalidade=0.5)
    validacao: ValidacaoOut = ValidacaoOut()
    uso: UsoOut | None = None
