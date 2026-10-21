"""Validação semântica pós-revisão.

Compara o catálogo de entidades protegidas **antes** e **depois** da revisão
por LLM e produz um :class:`ValidationReport` com achados:

* ``loss`` — entidade protegida que sumiu da revisão;
* ``alteration`` — entidade cujo valor mudou;
* ``invention`` — número presente na revisão e ausente do original (possível
  resultado fabricado).

O relatório implementa o portão de aprovação do `ADR-0013`: perda ou alteração
de entidade ``CRITICAL`` bloqueia a aprovação automática, assim como qualquer
número inventado.
"""

from __future__ import annotations

from collections import defaultdict
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.ir.protection import ProtectedEntity, ProtectedKind, ProtectionCatalog, ProtectionLevel

#: Janela (em code points) usada para casar "o mesmo lugar" no texto revisado.
_PROXIMIDADE = 80


class Severity(StrEnum):
    """Severidade de um achado de validação."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    INFO = "info"


class FindingCategory(StrEnum):
    """Categoria de um achado."""

    LOSS = "loss"
    ALTERATION = "alteration"
    INVENTION = "invention"


def _severidade_por_nivel(nivel: ProtectionLevel) -> Severity:
    """Traduz o nível de proteção da entidade para a severidade do achado."""
    if nivel is ProtectionLevel.CRITICAL:
        return Severity.CRITICAL
    if nivel is ProtectionLevel.HIGH:
        return Severity.HIGH
    if nivel is ProtectionLevel.MEDIUM:
        return Severity.MEDIUM
    return Severity.INFO


class ValidationFinding(BaseModel):
    """Um achado de validação semântica."""

    model_config = ConfigDict(frozen=True)

    severity: Severity
    category: FindingCategory
    entity_id: str = ""
    kind: str = ""
    level: str = ""
    before: str = ""
    after: str = ""
    start: int | None = None
    end: int | None = None
    message: str = ""
    suggested_action: str = ""


class ValidationReport(BaseModel):
    """Relatório de validação semântica."""

    model_config = ConfigDict(frozen=True)

    findings: tuple[ValidationFinding, ...] = ()
    """Achados, do mais grave para o menos grave."""

    entities_antes: int = 0
    entities_depois: int = 0
    perdas: int = 0
    alteracoes: int = 0
    invencoes: int = 0

    @property
    def blocked(self) -> bool:
        """Indica se a aprovação automática está bloqueada (ADR-0013)."""
        return any(
            achado.severity is Severity.CRITICAL or achado.category is FindingCategory.INVENTION
            for achado in self.findings
        )

    @property
    def has_critical(self) -> bool:
        return any(achado.severity is Severity.CRITICAL for achado in self.findings)


def validate(original: ProtectionCatalog, revised: ProtectionCatalog) -> ValidationReport:
    """Compara os catálogos e devolve o relatório de validação."""
    achados: list[ValidationFinding] = []
    fingerprints_revisados = revised.fingerprints()
    por_tipo: dict[ProtectedKind, list[ProtectedEntity]] = defaultdict(list)
    for entidade in revised.entities:
        por_tipo[entidade.kind].append(entidade)

    for entidade in original.iter_entities():
        if not entidade.fingerprint:
            continue
        if entidade.fingerprint in fingerprints_revisados:
            continue  # preservado

        vizinhas = [
            outra
            for outra in por_tipo.get(entidade.kind, [])
            if abs(outra.source_range.start - entidade.source_range.start) <= _PROXIMIDADE
        ]
        severidade = _severidade_por_nivel(entidade.level)
        if vizinhas:
            achados.append(
                ValidationFinding(
                    severity=severidade,
                    category=FindingCategory.ALTERATION,
                    entity_id=entidade.id,
                    kind=str(entidade.kind),
                    level=str(entidade.level),
                    before=entidade.text,
                    after=vizinhas[0].text,
                    start=entidade.source_range.start,
                    end=entidade.source_range.end,
                    message="valor de entidade protegida foi alterado",
                    suggested_action="reverter para o valor original e registrar a mudança",
                )
            )
        else:
            achados.append(
                ValidationFinding(
                    severity=severidade,
                    category=FindingCategory.LOSS,
                    entity_id=entidade.id,
                    kind=str(entidade.kind),
                    level=str(entidade.level),
                    before=entidade.text,
                    after="",
                    start=entidade.source_range.start,
                    end=entidade.source_range.end,
                    message="entidade protegida ausente na revisão",
                    suggested_action="restaurar o valor original",
                )
            )

    fingerprints_originais = original.fingerprints()
    for entidade in revised.iter_entities():
        if entidade.kind not in (ProtectedKind.NUMBER, ProtectedKind.STATISTIC):
            continue
        if not entidade.fingerprint or entidade.fingerprint in fingerprints_originais:
            continue
        achados.append(
            ValidationFinding(
                severity=Severity.HIGH,
                category=FindingCategory.INVENTION,
                entity_id=entidade.id,
                kind=str(entidade.kind),
                level=str(entidade.level),
                before="",
                after=entidade.text,
                start=entidade.source_range.start,
                end=entidade.source_range.end,
                message="número presente na revisão e ausente do original (possível invenção)",
                suggested_action="remover ou confirmar a origem do dado",
            )
        )

    achados.sort(key=lambda achado: _ordem(achado))
    return ValidationReport(
        findings=tuple(achados),
        entities_antes=len(original),
        entities_depois=len(revised),
        perdas=sum(1 for a in achados if a.category is FindingCategory.LOSS),
        alteracoes=sum(1 for a in achados if a.category is FindingCategory.ALTERATION),
        invencoes=sum(1 for a in achados if a.category is FindingCategory.INVENTION),
    )


def _ordem(achado: ValidationFinding) -> tuple[int, str]:
    """Ordena por severidade (decrescente) e depois pela categoria."""
    pesos = {
        Severity.CRITICAL: 0,
        Severity.HIGH: 1,
        Severity.MEDIUM: 2,
        Severity.INFO: 3,
    }
    return pesos.get(achado.severity, 9), achado.category
