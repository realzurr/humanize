"""Validação de integridade acadêmica (citações × referências).

Produz um relatório **auditável**: cada achado tem localização, severidade,
categoria, veredito e ação sugerida. O veredito distingue:

* ``erro_comprovado`` — violação objetiva (ex.: citação sem entrada);
* ``possivel_inconsistencia`` — indício que exige confirmação;
* ``nao_verificavel`` — impossível confirmar sem fonte externa;
* ``recomendacao_institucional`` — sugestão de conformidade.

Metadados de DOI são tratados como **propostas**, nunca aplicados
automaticamente.
"""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.services.references.citation_parser import parse_citations
from app.services.references.doi import DOIResolver
from app.services.references.matcher import match, uncited_references
from app.services.references.models import Citation, Reference, ReferenceType
from app.services.references.parser import parse_references

#: Campos mínimos por tipo de referência.
_REQUIRED_FIELDS: dict[ReferenceType, tuple[str, ...]] = {
    ReferenceType.ARTICLE: ("title", "year", "container"),
    ReferenceType.BOOK: ("title", "year"),
    ReferenceType.BOOK_SECTION: ("title", "year"),
    ReferenceType.THESIS: ("title", "year"),
    ReferenceType.DISSERTATION: ("title", "year"),
    ReferenceType.CONFERENCE: ("title", "year"),
    ReferenceType.WEB: ("title", "url"),
    ReferenceType.REPORT: ("title", "year"),
    ReferenceType.LEGAL: ("title",),
    ReferenceType.OTHER: ("title",),
}


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(StrEnum):
    MISSING_REFERENCE = "missing_reference"
    UNCITED_REFERENCE = "uncited_reference"
    DUPLICATE = "duplicate"
    MISSING_FIELD = "missing_field"
    METADATA_MISMATCH = "metadata_mismatch"


class Verdict(StrEnum):
    ERRO_COMPROVADO = "erro_comprovado"
    POSSIVEL_INCONSISTENCIA = "possivel_inconsistencia"
    NAO_VERIFICAVEL = "nao_verificavel"
    RECOMENDACAO_INSTITUCIONAL = "recomendacao_institucional"


class Finding(BaseModel):
    """Achado auditável da validação."""

    model_config = ConfigDict(frozen=True)

    severity: Severity
    category: FindingCategory
    verdict: Verdict
    line: int | None = None
    start: int | None = None
    end: int | None = None
    message: str = ""
    suggested_action: str = ""
    confidence: str = ""


class ValidationReport(BaseModel):
    """Relatório de validação acadêmica."""

    model_config = ConfigDict(frozen=True)

    findings: tuple[Finding, ...] = ()
    citacoes: int = 0
    referencias: int = 0
    associadas: int = 0
    """Citações associadas a uma referência."""


async def validate(
    text: str,
    *,
    lookup_doi: bool = False,
    doi_resolver: DOIResolver | None = None,
) -> ValidationReport:
    """Valida as citações e referências do texto, devolvendo o relatório."""
    citacoes = parse_citations(text)
    referencias = parse_references(text)
    associacoes = match(citacoes, referencias)

    citacoes_por_id = {c.id: c for c in citacoes}
    achados: list[Finding] = []

    for associacao in associacoes:
        if associacao.reference_id is not None:
            continue
        citacao = citacoes_por_id.get(associacao.citation_id)
        achados.append(
            Finding(
                severity=Severity.HIGH,
                category=FindingCategory.MISSING_REFERENCE,
                verdict=Verdict.POSSIVEL_INCONSISTENCIA,
                line=_linha(text, citacao),
                start=_inicio(citacao),
                end=_fim(citacao),
                message="citação sem entrada correspondente na lista de referências",
                suggested_action="adicionar a entrada de referência ou corrigir a citação",
                confidence=associacao.confidence,
            )
        )

    for referencia in uncited_references(associacoes, referencias):
        achados.append(
            Finding(
                severity=Severity.INFO,
                category=FindingCategory.UNCITED_REFERENCE,
                verdict=Verdict.NAO_VERIFICAVEL,
                line=_linha(text, referencia),
                start=_inicio(referencia),
                end=_fim(referencia),
                message="entrada de referência sem citação no texto",
                suggested_action="verificar se a referência foi de fato usada",
            )
        )

    for referencia in _duplicadas(referencias):
        achados.append(
            Finding(
                severity=Severity.LOW,
                category=FindingCategory.DUPLICATE,
                verdict=Verdict.POSSIVEL_INCONSISTENCIA,
                line=_linha(text, referencia),
                start=_inicio(referencia),
                end=_fim(referencia),
                message="possível referência duplicada",
                suggested_action="unificar as entradas duplicadas",
            )
        )

    for referencia in referencias:
        for campo in _campos_ausentes(referencia):
            achados.append(
                Finding(
                    severity=Severity.MEDIUM,
                    category=FindingCategory.MISSING_FIELD,
                    verdict=Verdict.POSSIVEL_INCONSISTENCIA,
                    line=_linha(text, referencia),
                    start=_inicio(referencia),
                    end=_fim(referencia),
                    message=f"campo bibliográfico obrigatório ausente: {campo}",
                    suggested_action="preencher o campo ausente",
                )
            )

    if lookup_doi and doi_resolver is not None:
        for referencia in referencias:
            if not referencia.doi:
                continue
            metadata = await doi_resolver.fetch_metadata(referencia.doi)
            if metadata is None:
                continue
            for mudanca in doi_resolver.propose_changes(referencia, metadata):
                achados.append(
                    Finding(
                        severity=Severity.MEDIUM,
                        category=FindingCategory.METADATA_MISMATCH,
                        verdict=Verdict.POSSIVEL_INCONSISTENCIA,
                        line=_linha(text, referencia),
                        start=_inicio(referencia),
                        end=_fim(referencia),
                        message=(
                            f"metadado {mudanca.field} diverge do DOI "
                            f"({mudanca.current!r} → {mudanca.proposed!r})"
                        ),
                        suggested_action="aprovar ou rejeitar a alteração proposta",
                        confidence=mudanca.confidence,
                    )
                )

    achados.sort(key=lambda f: (_peso(f.severity), f.line or 0))
    return ValidationReport(
        findings=tuple(achados),
        citacoes=len(citacoes),
        referencias=len(referencias),
        associadas=sum(1 for a in associacoes if a.reference_id is not None),
    )


def _campos_ausentes(referencia: Reference) -> list[str]:
    obrigatorios = _REQUIRED_FIELDS.get(referencia.type, ("title",))
    return [campo for campo in obrigatorios if not getattr(referencia, campo, "")]


def _duplicadas(referencias: list[Reference]) -> list[Reference]:
    vistas: dict[tuple[str, str], str] = {}
    duplicadas: list[Reference] = []
    for referencia in referencias:
        chave = (
            referencia.first_surname.lower(),
            _normalizar(referencia.title),
        )
        if chave in vistas:
            duplicadas.append(referencia)
        else:
            vistas[chave] = referencia.id
    return duplicadas


def _linha(text: str, obj: Citation | Reference | None) -> int | None:
    inicio = _inicio(obj)
    if inicio is None:
        return None
    return text.count("\n", 0, inicio) + 1


def _inicio(obj: Citation | Reference | None) -> int | None:
    if obj is None or obj.source_range is None:
        return None
    return obj.source_range.start


def _fim(obj: Citation | Reference | None) -> int | None:
    if obj is None or obj.source_range is None:
        return None
    return obj.source_range.end


def _normalizar(valor: str) -> str:
    return re.sub(r"\s+", " ", valor).strip().lower()


def _peso(severity: Severity) -> int:
    return {
        Severity.CRITICAL: 0,
        Severity.HIGH: 1,
        Severity.MEDIUM: 2,
        Severity.LOW: 3,
        Severity.INFO: 4,
    }[severity]
