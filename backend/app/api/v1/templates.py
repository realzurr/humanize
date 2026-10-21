"""Rotas de templates acadêmicos (v1).

Lista, detalha e resolve templates. A resolução aplica a precedência do
`ADR-0007` (instituição > template > norma) e registra os conflitos — que são
devolvidos ao cliente, nunca ocultados.
"""

from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, Request

from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.schemas.templates import ResolveOut, TemplateSummary
from app.services.academic.templates import TemplateNotFoundError, TemplateRegistry

router = APIRouter(tags=["templates"])

logger = get_logger(__name__)


def _registro(request: Request) -> TemplateRegistry:
    return cast(TemplateRegistry, request.app.state.template_registry)


@router.get("/templates", response_model=list[TemplateSummary])
async def listar_templates(request: Request) -> list[TemplateSummary]:
    """Lista os templates disponíveis (ABNT e institucionais)."""
    registro = _registro(request)
    resumos: list[TemplateSummary] = []
    for template_id in registro.ids():
        raw = registro.raw(template_id)
        resumos.append(
            TemplateSummary(
                id=template_id,
                kind=str(raw.get("kind", "")),
                title=str(raw.get("title", "")),
                version=str(raw.get("version", "")),
                extends=raw.get("extends"),
                institution=raw.get("institution"),
                fontes=len(raw.get("sources", [])),
            )
        )
    return resumos


@router.get("/templates/{template_id}")
async def detalhar_template(template_id: str, request: Request) -> dict[str, Any]:
    """Devolve o template (com a herança já resolvida)."""
    registro = _registro(request)
    try:
        template = registro.get(template_id)
    except TemplateNotFoundError as exc:
        raise NotFoundError(str(exc)) from exc
    return template.model_dump()


@router.get("/templates/{template_id}/resolve", response_model=ResolveOut)
async def resolver_template(
    template_id: str,
    request: Request,
    instituicao: str | None = None,
) -> ResolveOut:
    """Resolve o template, aplicando o perfil institucional se informado."""
    registro = _registro(request)
    try:
        resolvido = registro.resolve(template_id, instituicao)
    except TemplateNotFoundError as exc:
        raise NotFoundError(str(exc)) from exc

    if resolvido.conflicts:
        logger.info(
            "template.resolvido_com_conflitos",
            template=template_id,
            instituicao=instituicao,
            conflitos=len(resolvido.conflicts),
        )

    return ResolveOut(
        template=resolvido.template,
        conflicts=list(resolvido.conflicts),
        overrides=list(resolvido.overrides),
    )
