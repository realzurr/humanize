"""Rotas de normalização textual (v1).

Endpoint único da Onda 1. A rota apenas valida a entrada, chama o motor e
serializa o relatório — nenhuma regra de normalização mora na camada de API.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace

from fastapi import APIRouter

from app.core.logging import get_logger
from app.schemas.normalize import (
    EntidadeProtegidaOut,
    NormalizeRequest,
    NormalizeResponse,
    TransformacaoOut,
)
from app.services.normalizer.engine import NormalizationEngine
from app.services.normalizer.profile import describe_profiles, get_profile

router = APIRouter(tags=["normalização"])

logger = get_logger(__name__)

#: Motor compartilhado entre as requisições. As regras são imutáveis.
_engine = NormalizationEngine()


@router.post("/normalize", response_model=NormalizeResponse)
async def normalize(requisicao: NormalizeRequest) -> NormalizeResponse:
    """Normaliza um texto e devolve o texto, o relatório e as entidades protegidas."""
    perfil_base = get_profile(requisicao.perfil)
    perfil = perfil_base.with_options(requisicao.opcoes)
    if requisicao.regras_desativadas:
        perfil = replace(
            perfil,
            disabled_rules=frozenset(perfil.disabled_rules | set(requisicao.regras_desativadas)),
        )

    resultado = await asyncio.to_thread(_engine.run, requisicao.texto, perfil)
    report = resultado.report

    logger.info(
        "normalizacao.concluida",
        caracteres_antes=report.total_caracteres_antes,
        caracteres_depois=report.total_caracteres_depois,
        regras_acionadas=len(report.transformacoes),
        entidades_protegidas=len(report.entidades_protegidas),
        avisos=len(report.avisos),
    )

    if report.houve_perda:
        logger.warning(
            "normalizacao.perda_de_conteudo_protegido",
            avisos=list(report.avisos),
        )

    return NormalizeResponse(
        texto=resultado.text,
        transformacoes=[
            TransformacaoOut(
                stage=transformacao.stage,
                rule_id=transformacao.rule_id,
                description=transformacao.description,
                category=transformacao.category,
                count=transformacao.count,
                severity=transformacao.severity,
                before=transformacao.before,
                after=transformacao.after,
            )
            for transformacao in report.transformacoes
        ],
        total_caracteres_antes=report.total_caracteres_antes,
        total_caracteres_depois=report.total_caracteres_depois,
        entidades_protegidas=[
            EntidadeProtegidaOut(
                id=entidade.id,
                kind=entidade.kind,
                text=entidade.text,
                start=entidade.start,
                end=entidade.end,
                level=entidade.level,
                fingerprint=entidade.fingerprint,
            )
            for entidade in report.entidades_protegidas
        ],
        regras_desativadas=list(report.regras_desativadas),
        avisos=list(report.avisos),
    )


@router.get("/normalize/perfis")
async def perfis() -> list[dict[str, object]]:
    """Lista os perfis de normalização disponíveis."""
    return describe_profiles()
