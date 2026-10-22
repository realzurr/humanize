"""Motor de humanização semântica.

Orquestra o ciclo completo: análise do texto, extração e máscara das entidades
protegidas, chamada ao provedor de LLM, restauração dos valores originais e
validação semântica pós-revisão. O motor **não** aprova nada sozinho — o
relatório de validação (com o portão de aprovação do `ADR-0013`) é devolvido
junto com o texto revisado.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.services.humanizer.analysis import AnalysisReport, analyze
from app.services.humanizer.intensity import Intensity
from app.services.humanizer.intensity import instruction as instrucao_de_intensidade
from app.services.humanizer.profiles import AuthorialProfile
from app.services.humanizer.style_features import StyleFeatures, extract_style_features
from app.services.ingestion.guard import INSTRUCAO_SISTEMA, envolver_conteudo, remover_envoltorio
from app.services.providers.base import ChatMessage, LLMProvider, LLMRequest, TokenUsage
from app.services.semantic_validator import extract, mask, unmask, validate
from app.services.semantic_validator.validator import ValidationReport


class ReviewResult(BaseModel):
    """Resultado de uma humanização."""

    model_config = ConfigDict(frozen=True)

    texto: str
    """Texto revisado (com as entidades protegidas restauradas ao original)."""

    perfil: str
    intensidade: int
    modelo: str = ""
    provedor: str = ""

    analise: AnalysisReport = AnalysisReport()
    estilo: StyleFeatures = StyleFeatures(formalidade=0.5)

    validacao: ValidationReport = ValidationReport()
    """Relatório de validação semântica (perda/alterção/invenção)."""

    uso: TokenUsage | None = None
    """Consumo de tokens e custo estimado, quando houve chamada."""

    bloqueado: bool = False
    """Se a aprovação automática está bloqueada (ADR-0013)."""

    metadata: dict[str, Any] = Field(default_factory=dict)


class HumanizerService:
    """Executa a humanização com um provedor de LLM injetado."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def humanize(
        self,
        text: str,
        *,
        profile: AuthorialProfile,
        intensity: Intensity,
        model: str,
    ) -> ReviewResult:
        """Humaniza o texto conforme o perfil, a intensidade e o modelo."""
        analise = analyze(text)
        estilo = extract_style_features(text)

        if not text.strip() or intensity is Intensity.NENHUMA:
            return ReviewResult(
                texto=text,
                perfil=profile.id,
                intensidade=int(intensity),
                modelo=model,
                provedor=str(self._provider.provider_id),
                analise=analise,
                estilo=estilo,
            )

        catalog = extract(text)
        mascarado = mask(text, catalog)

        request = self._build_request(
            text=mascarado.text, profile=profile, intensity=intensity, model=model
        )
        resposta = await self._provider.generate(request)

        revisado = unmask(resposta.text, mascarado)
        revisado = remover_envoltorio(revisado)
        novo_catalog = extract(revisado)
        validacao = validate(catalog, novo_catalog)

        return ReviewResult(
            texto=revisado,
            perfil=profile.id,
            intensidade=int(intensity),
            modelo=model,
            provedor=str(self._provider.provider_id),
            analise=analise,
            estilo=estilo,
            validacao=validacao,
            uso=resposta.usage,
            bloqueado=validacao.blocked,
            metadata={
                "entidades_antes": len(catalog),
                "entidades_depois": len(novo_catalog),
            },
        )

    def _build_request(
        self,
        *,
        text: str,
        profile: AuthorialProfile,
        intensity: Intensity,
        model: str,
    ) -> LLMRequest:
        sistema = self._prompt_de_sistema(profile, intensity)
        return LLMRequest(
            messages=(
                ChatMessage(role="system", content=sistema),
                ChatMessage(role="user", content=envolver_conteudo(text)),
            ),
            model=model,
            temperature=0.7,
        )

    def _prompt_de_sistema(self, profile: AuthorialProfile, intensity: Intensity) -> str:
        partes = [
            profile.system_instruction,
            instrucao_de_intensidade(intensity),
            INSTRUCAO_SISTEMA,
            (
                "O texto enviado contém marcadores entre ⟦ ⟧ (ex.: ⟦P0001⟧) que "
                "representam valores protegidos. Reproduza esses marcadores "
                "exatamente como estão, sem alterá-los, removê-los ou expandi-los."
            ),
        ]
        return "\n\n".join(partes)
