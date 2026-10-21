"""Rotas de validação acadêmica (v1).

Valida a integridade de citações e referências e devolve um relatório
auditável. A consulta de metadados de DOI é **opt-in** (requer
``consultar_doi=true`` e ``Settings.enable_doi_lookup=true``) e apenas gera
**propostas** — nada é aplicado automaticamente.
"""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Request

from app.core.config import Settings
from app.core.logging import get_logger
from app.schemas.academic import (
    AcademicValidateRequest,
    AcademicValidateResponse,
    FindingOut,
)
from app.services.references.doi import DOIResolver
from app.services.references.validator import ValidationReport, validate

router = APIRouter(tags=["acadêmico"])

logger = get_logger(__name__)


@router.post("/academic/validate", response_model=AcademicValidateResponse)
async def validar(corpo: AcademicValidateRequest, request: Request) -> AcademicValidateResponse:
    """Valida citações e referências do texto e devolve o relatório."""
    settings = cast(Settings, request.app.state.settings)
    lookup = corpo.consultar_doi and settings.enable_doi_lookup
    resolver = cast(DOIResolver, request.app.state.doi_resolver) if lookup else None

    report = await validate(corpo.texto, lookup_doi=lookup, doi_resolver=resolver)

    logger.info(
        "validacao.concluida",
        citacoes=report.citacoes,
        referencias=report.referencias,
        associadas=report.associadas,
        achados=len(report.findings),
    )

    return _para_saida(report)


def _para_saida(report: ValidationReport) -> AcademicValidateResponse:
    return AcademicValidateResponse(
        achados=[
            FindingOut(
                severidade=str(achado.severity),
                categoria=str(achado.category),
                veredito=str(achado.verdict),
                linha=achado.line,
                inicio=achado.start,
                fim=achado.end,
                mensagem=achado.message,
                acao_sugerida=achado.suggested_action,
                confianca=achado.confidence,
            )
            for achado in report.findings
        ],
        citacoes=report.citacoes,
        referencias=report.referencias,
        associadas=report.associadas,
    )
