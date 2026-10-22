"""Rota de humanização semântica (v1).

A rota resolve o perfil, valida a intensidade, constrói o provedor pelo
registro e delega o ciclo completo ao :class:`HumanizerService`. O texto
revisado, o relatório de validação (com o portão de aprovação) e o consumo
estimado são devolvidos ao cliente.
"""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    make_rate_limit_dependency,
    owner_id_of,
    resolve_provider_key,
)
from app.core.database import get_session
from app.core.errors import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.humanize import (
    AchadoOut,
    HumanizeRequest,
    HumanizeResponse,
    UsoOut,
    ValidacaoOut,
)
from app.services.humanizer.engine import HumanizerService
from app.services.humanizer.intensity import Intensity
from app.services.humanizer.intensity import validate as validar_intensidade
from app.services.humanizer.profiles import (
    AUTORAL_ID,
    AuthorialProfile,
    build_autoral_profile,
    get_profile,
)
from app.services.providers.base import LLMProvider, TokenUsage
from app.services.providers.registry import ProviderRegistry
from app.services.semantic_validator.validator import ValidationReport

router = APIRouter(tags=["humanização"])

logger = get_logger(__name__)

humanize_rate_limit = make_rate_limit_dependency("humanize")

#: Limite de caracteres de cada texto autoral.
_MAX_AUTORAL_TEXT_LENGTH = 50_000


@router.post("/humanize", response_model=HumanizeResponse)
async def humanize(
    requisicao: HumanizeRequest,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    usuario: Annotated[User | None, Depends(get_current_user)],
    _: Annotated[None, Depends(humanize_rate_limit)],
) -> HumanizeResponse:
    """Humaniza o texto preservando números, datas, DOIs e citações."""
    owner_id = owner_id_of(usuario)
    perfil = _resolver_perfil(requisicao, owner_id)
    intensidade = _validar_intensidade(requisicao.intensidade)

    registro = cast(ProviderRegistry, request.app.state.provider_registry)
    chave = resolve_provider_key(request, session, requisicao.provedor, owner_id)
    provedor = _resolver_provedor(registro, requisicao.provedor, chave)
    modelo = requisicao.modelo or await _modelo_padrao(provedor)

    servico = HumanizerService(provedor)
    resultado = await servico.humanize(
        requisicao.texto,
        profile=perfil,
        intensity=intensidade,
        model=modelo,
    )

    report = resultado.validacao
    logger.info(
        "humanizacao.concluida",
        perfil=resultado.perfil,
        intensidade=resultado.intensidade,
        bloqueado=resultado.bloqueado,
        perdas=report.perdas,
        alteracoes=report.alteracoes,
        invencoes=report.invencoes,
    )
    if resultado.bloqueado:
        logger.warning("humanizacao.bloqueada", achados=len(report.findings))

    return HumanizeResponse(
        texto=resultado.texto,
        perfil=resultado.perfil,
        intensidade=resultado.intensidade,
        modelo=resultado.modelo,
        provedor=resultado.provedor,
        bloqueado=resultado.bloqueado,
        analise=resultado.analise,
        estilo=resultado.estilo,
        validacao=_validacao_para_saida(report),
        uso=_uso_para_saida(resultado.uso),
    )


def _resolver_perfil(requisicao: HumanizeRequest, owner_id: str | None) -> AuthorialProfile:
    if requisicao.perfil == AUTORAL_ID:
        # Com autenticação ativa, o owner_id vem do token (nunca do JSON do
        # cliente); no modo local, usa-se o valor informado na requisição.
        dono = owner_id or requisicao.owner_id or ""
        try:
            return build_autoral_profile(
                dono,
                tuple(t[:_MAX_AUTORAL_TEXT_LENGTH] for t in requisicao.textos_autorais),
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
    perfil = get_profile(requisicao.perfil)
    if perfil is None:
        raise NotFoundError(f"perfil desconhecido: {requisicao.perfil}")
    return perfil


def _validar_intensidade(valor: int) -> Intensity:
    try:
        return validar_intensidade(valor)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc


def _resolver_provedor(
    registro: ProviderRegistry,
    provider_id: str,
    chave: str | None,
) -> LLMProvider:
    try:
        return registro.build(provider_id, api_key=chave)
    except ValueError as exc:
        raise NotFoundError(str(exc)) from exc


async def _modelo_padrao(provedor: LLMProvider) -> str:
    for info in await provedor.list_models():
        return info.id
    return ""


def _validacao_para_saida(report: ValidationReport) -> ValidacaoOut:
    return ValidacaoOut(
        achados=[
            AchadoOut(
                severidade=str(achado.severity),
                categoria=str(achado.category),
                entidade_id=achado.entity_id,
                tipo=achado.kind,
                nivel=achado.level,
                antes=achado.before,
                depois=achado.after,
                mensagem=achado.message,
                acao_sugerida=achado.suggested_action,
            )
            for achado in report.findings
        ],
        entidades_antes=report.entities_antes,
        entidades_depois=report.entities_depois,
        perdas=report.perdas,
        alteracoes=report.alteracoes,
        invencoes=report.invencoes,
        bloqueado=report.blocked,
    )


def _uso_para_saida(uso: TokenUsage | None) -> UsoOut | None:
    if uso is None:
        return None
    return UsoOut(
        prompt_tokens=uso.prompt_tokens,
        completion_tokens=uso.completion_tokens,
        total_tokens=uso.total_tokens,
        custo_estimado_usd=uso.estimated_cost_usd,
    )
