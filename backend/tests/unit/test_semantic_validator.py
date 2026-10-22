"""Testes do validador semântico e da máscara."""

from __future__ import annotations

from app.ir.protection import (
    ProtectedEntity,
    ProtectedKind,
    ProtectionCatalog,
    ProtectionLevel,
)
from app.ir.spans import SourceRange
from app.services.semantic_validator import extract, mask, unmask, validate
from app.services.semantic_validator.masker import placeholders_reproduzidos
from app.services.semantic_validator.validator import FindingCategory, Severity


def test_validate_sem_perdas() -> None:
    texto = "O valor foi 45,5 % no dia 12/03/2025."
    original = extract(texto)
    revisado = extract(texto)
    report = validate(original, revisado)
    assert report.perdas == 0
    assert report.alteracoes == 0
    assert report.invencoes == 0
    assert not report.blocked


def test_validate_detecta_perda() -> None:
    original = extract("O valor foi 45,5 %.")
    revisado = extract("O valor foi medido.")
    report = validate(original, revisado)
    assert report.perdas == 1
    assert any(f.category is FindingCategory.LOSS for f in report.findings)


def test_validate_perda_de_numero_e_critica() -> None:
    original = extract("O resultado foi 45 %.")
    revisado = extract("O resultado foi divulgado.")
    report = validate(original, revisado)
    perda = next(f for f in report.findings if f.category is FindingCategory.LOSS)
    assert perda.severity is Severity.CRITICAL
    assert report.blocked


def test_validate_detecta_alteracao() -> None:
    original = extract("O valor foi 45 %.")
    revisado = extract("O valor foi 45,5 %.")
    report = validate(original, revisado)
    assert report.alteracoes >= 1
    assert any(f.category is FindingCategory.ALTERATION for f in report.findings)


def test_validate_detecta_invencao() -> None:
    original = extract("O estudo foi conduzido em campo.")
    revisado = extract("O estudo foi conduzido em campo, com 87 % de adesão.")
    report = validate(original, revisado)
    assert report.invencoes >= 1
    assert any(f.category is FindingCategory.INVENTION for f in report.findings)
    assert report.blocked  # invenção bloqueia aprovação (ADR-0013)


def test_mascara_e_restaura() -> None:
    texto = "O valor foi 45,5 % e a DOI 10.1111/jss.12845."
    catalog = extract(texto)
    mascarado = mask(texto, catalog)
    # O texto mascarado não contém os valores originais.
    assert "45,5" not in mascarado.text
    assert "10.1111" not in mascarado.text
    # A restauração devolve o original intacto.
    assert unmask(mascarado.text, mascarado) == texto


def test_mascara_placeholders_estaveis() -> None:
    texto = "Valor 45 % e 12 %."
    catalog = extract(texto)
    mascarado = mask(texto, catalog)
    assert mascarado.text.count("⟦P") == 2
    reproduzidos = placeholders_reproduzidos(mascarado.text, mascarado)
    assert len(reproduzidos) == 2


def test_unmask_ignora_placeholder_desconhecido() -> None:
    texto = "Valor 45 %."
    catalog = extract(texto)
    mascarado = mask(texto, catalog)
    resultado = unmask(mascarado.text + " ⟦P9999⟧", mascarado)
    assert "⟦P9999⟧" in resultado  # placeholder desconhecido permanece


def _catalogo(start: int, texto: str, valor_fp: str) -> ProtectionCatalog:
    entidade = ProtectedEntity(
        id="P0001",
        kind=ProtectedKind.NUMBER,
        text=texto,
        source_range=SourceRange(start=start, end=start + len(texto)),
        level=ProtectionLevel.CRITICAL,
        fingerprint=valor_fp,
    )
    return ProtectionCatalog(entities=(entidade,))


def test_proximidade_80_code_points_gera_alteracao() -> None:
    """GAP-07: na distância exata de 80 code points, a divergência é ALTERATION."""
    original = _catalogo(0, "45", "fp-original")
    revisado = _catalogo(80, "45,5", "fp-alterado")
    report = validate(original, revisado)
    assert any(f.category is FindingCategory.ALTERATION for f in report.findings)


def test_proximidade_81_code_points_gera_perda() -> None:
    """GAP-07: além de 80 code points, a divergência é tratada como LOSS."""
    original = _catalogo(0, "45", "fp-original")
    revisado = _catalogo(81, "45,5", "fp-alterado")
    report = validate(original, revisado)
    assert any(f.category is FindingCategory.LOSS for f in report.findings)
    assert not any(f.category is FindingCategory.ALTERATION for f in report.findings)


def test_report_has_critical() -> None:
    original = _catalogo(0, "45", "fp-original")
    revisado = _catalogo(100, "45,5", "fp-alterado")
    report = validate(original, revisado)
    assert report.has_critical
