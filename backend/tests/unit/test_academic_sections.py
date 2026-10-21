"""Testes da classificação de elementos estruturais e do sumário TOC."""

from __future__ import annotations

from app.services.academic.sections import (
    TOC_IS_FIELD,
    classify,
    is_post_textual,
    is_pre_textual,
    is_textual,
)


def test_classificacao_pre_textual() -> None:
    assert is_pre_textual("cover")
    assert is_pre_textual("abstract_pt")
    assert is_pre_textual("table_of_contents")


def test_classificacao_textual() -> None:
    assert is_textual("introduction")
    assert is_textual("development")
    assert is_textual("conclusion")


def test_classificacao_pos_textual() -> None:
    assert is_post_textual("references")
    assert is_post_textual("appendix")
    assert is_post_textual("index")


def test_classify_devolve_categoria() -> None:
    assert classify("cover") == "pre_textual"
    assert classify("development") == "textual"
    assert classify("references") == "pos_textual"
    assert classify("desconhecido") == "outro"


def test_sumario_e_campo_toc_real() -> None:
    assert TOC_IS_FIELD is True
