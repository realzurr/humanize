"""Testes do extrator de entidades protegidas."""

from __future__ import annotations

import pytest

from app.ir.protection import ProtectedKind
from app.services.normalizer.protect import (
    build_catalog,
    detect_protected_spans,
    free_spans,
)


def _kinds(texto: str) -> list[ProtectedKind]:
    return [span.kind for span in detect_protected_spans(texto)]


def test_detecta_numero() -> None:
    assert ProtectedKind.NUMBER in _kinds("a concentração foi 45,5 % do total")


def test_detecta_formula_com_superindice() -> None:
    assert ProtectedKind.FORMULA in _kinds("o valor foi 10⁻⁶ m²")


def test_detecta_formula_com_grego() -> None:
    assert ProtectedKind.FORMULA in _kinds("a eficiência η foi estimada")


def test_detecta_url() -> None:
    assert ProtectedKind.URL in _kinds("veja https://doi.org/10.1590/abc")


def test_detecta_doi() -> None:
    assert ProtectedKind.DOI in _kinds("DOI: 10.1111/jss.12845.")


def test_detecta_citacao_autor_data() -> None:
    assert ProtectedKind.CITATION in _kinds("conforme (Silva, 2020), ...")


def test_detecta_citacao_numerica() -> None:
    assert ProtectedKind.CITATION in _kinds("resultado [12] indica")


def test_detecta_citacao_literal() -> None:
    assert ProtectedKind.QUOTE_LITERAL in _kinds("“citação literal preservada”")


def test_detecta_tabela_markdown() -> None:
    texto = "| A | B |\n|---|---|\n| 1 | 2 |\n"
    assert ProtectedKind.TABLE in _kinds(texto)


def test_detecta_bloco_de_codigo() -> None:
    texto = "```\nprint('x')\n```"
    assert ProtectedKind.CODE in _kinds(texto)


def test_detecta_unidade() -> None:
    assert ProtectedKind.UNIT in _kinds("a massa foi 12,3 kg")


def test_detecta_referencia_em_lista() -> None:
    texto = "## REFERÊNCIAS\nSILVA, R. A. Título. São Paulo: Editora, 2020.\n"
    assert ProtectedKind.REFERENCE in _kinds(texto)


def test_nao_sobrepoe_intervalos() -> None:
    spans = detect_protected_spans("a 10⁻⁶ m² e 45,5 % (Silva, 2020).")
    for i, atual in enumerate(spans):
        for outra in spans[i + 1 :]:
            assert not atual.overlaps(outra)


def test_free_spans_complementa_protegidos() -> None:
    texto = "abc123def"
    spans = detect_protected_spans(texto)
    livres = free_spans(texto, spans)
    reconstruido = ""
    cursor = 0
    for inicio, fim in livres:
        reconstruido += texto[cursor:inicio]
        reconstruido += texto[inicio:fim]
        cursor = fim
    reconstruido += texto[cursor:]
    # O trecho livre nunca deve incluir conteúdo protegido.
    for inicio, fim in livres:
        for span in spans:
            assert not (inicio < span.end and span.start < fim)


def test_build_catalog_atribui_fingerprint_e_nivel() -> None:
    catalog = build_catalog("a concentração foi 45,5 %")
    entidades = list(catalog.iter_entities())
    assert entidades
    numero = next(e for e in entidades if e.kind is ProtectedKind.NUMBER)
    assert numero.fingerprint
    assert numero.id.startswith("P")
    assert numero.source_range.start < numero.source_range.end


@pytest.mark.parametrize(
    ("texto", "preservado"),
    [
        ("10⁻⁶", True),
        ("x²", True),
        ("Na⁺", True),
        ("CO₂", True),
        ("E = m·a", True),
        ("η = (Ea − Ec) / Ea × 100", True),
        ("a − b", True),
    ],
)
def test_notacao_cientifica_protegida(texto: str, preservado: bool) -> None:
    kinds = _kinds(texto)
    tem_formula = ProtectedKind.FORMULA in kinds
    assert tem_formula is preservado
