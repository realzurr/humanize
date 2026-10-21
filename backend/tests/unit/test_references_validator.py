"""Testes do relatório de validação acadêmica."""

from __future__ import annotations

from app.services.references.validator import (
    FindingCategory,
    Severity,
    Verdict,
    validate,
)


async def test_citacao_sem_referencia() -> None:
    texto = "(SOUZA, 2020)\n\n## REFERÊNCIAS\n\nSILVA, R. A. Título. Revista, 2020."
    report = await validate(texto)
    achado = next(f for f in report.findings if f.category is FindingCategory.MISSING_REFERENCE)
    assert achado.severity is Severity.HIGH
    assert achado.verdict is Verdict.POSSIVEL_INCONSISTENCIA
    assert achado.line is not None


async def test_referencia_nao_citada() -> None:
    texto = (
        "(SILVA, 2020)\n\n## REFERÊNCIAS\n\n"
        "SILVA, R. A. Título. Revista, 2020.\n\nSOUZA, M. Outro. 2021."
    )
    report = await validate(texto)
    achado = next(f for f in report.findings if f.category is FindingCategory.UNCITED_REFERENCE)
    assert achado.severity is Severity.INFO
    assert achado.verdict is Verdict.NAO_VERIFICAVEL


async def test_campo_ausente() -> None:
    # Força uma entrada sem ano, por exemplo.
    texto_sem_ano = "(SILVA, 2020)\n\n## REFERÊNCIAS\n\nSILVA, R. A. Título sem ano."
    report = await validate(texto_sem_ano)
    assert any(f.category is FindingCategory.MISSING_FIELD for f in report.findings)


async def test_duplicata() -> None:
    texto = (
        "(SILVA, 2020)\n\n## REFERÊNCIAS\n\n"
        "SILVA, R. A. Título. Revista, 2020.\n\nSILVA, R. A. Título. Revista, 2020."
    )
    report = await validate(texto)
    assert any(f.category is FindingCategory.DUPLICATE for f in report.findings)


async def test_relatorio_auditavel_campos_presentes() -> None:
    texto = "(SOUZA, 2020)\n\n## REFERÊNCIAS\n\nSILVA, R. A. Título. Revista, 2020."
    report = await validate(texto)
    achado = report.findings[0]
    # Todo achado tem localização, severidade, categoria e ação sugerida.
    assert achado.severity is not None
    assert achado.category is not None
    assert achado.line is not None
    assert achado.suggested_action


async def test_validacao_completa_sem_achados() -> None:
    texto = "(SILVA, 2020)\n\n## REFERÊNCIAS\n\nSILVA, R. A. Título. Revista, 2020."
    report = await validate(texto)
    assert report.associadas == 1
    assert report.citacoes == 1
    assert report.referencias == 1
