"""Testes de validação de metadados."""

from __future__ import annotations

from app.ir.document import DocumentMetadata
from app.services.academic.metadata import missing_fields, required_fields


def test_campos_obrigatorios_de_tese() -> None:
    campos = required_fields("tese")
    assert "author" in campos and "title" in campos and "advisor" in campos


def test_metadados_completos_nao_faltam() -> None:
    metadata = DocumentMetadata(
        institution="UFMS",
        author="Fulano",
        title="Título",
        advisor="Orientador",
        year="2026",
        city="Campo Grande",
    )
    assert missing_fields("tese", metadata) == []


def test_metadados_incompletos_sao_listados() -> None:
    metadata = DocumentMetadata(author="Fulano")
    faltando = missing_fields("tese", metadata)
    assert "title" in faltando
    assert "advisor" in faltando


def test_natureza_desconhecida_usa_campos_comuns() -> None:
    campos = required_fields("desconhecida")
    assert "author" in campos and "title" in campos
