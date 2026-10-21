"""Testes de resolução de estilos."""

from __future__ import annotations

from app.services.academic.styles import available_styles, style_for_kind, style_for_level
from app.services.academic.template_model import Estilo


def test_estilo_por_nivel() -> None:
    styles = {
        "heading1": Estilo(bold=True),
        "heading2": Estilo(bold=True),
        "heading3": Estilo(italic=True),
    }
    assert style_for_level(styles, 1).bold is True
    assert style_for_level(styles, 3).italic is True


def test_nivel_sem_estilo_devolve_padrao() -> None:
    assert style_for_level({}, 1).bold is False
    assert style_for_level({}, 5).bold is False


def test_estilo_por_tipo() -> None:
    styles = {"citacao_longa": Estilo(font_size_pt=10, indent_cm=4)}
    assert style_for_kind(styles, "citacao_longa").font_size_pt == 10


def test_tipo_sem_estilo_devolve_padrao() -> None:
    assert style_for_kind({}, "legenda").font_size_pt is None


def test_available_styles_ordenados() -> None:
    styles = {"heading2": Estilo(), "heading1": Estilo()}
    assert available_styles(styles) == ("heading1", "heading2")
