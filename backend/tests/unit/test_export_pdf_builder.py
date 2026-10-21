"""Testes unitários do renderizador de PDF em processo isolado e comparador DOCX↔PDF."""

from __future__ import annotations

import pymupdf
import pytest

from app.ir.document import AcademicDocument, DocumentMetadata
from app.services.academic.templates import TemplateRegistry
from app.services.document_export.docx_builder import build_docx
from app.services.document_export.pdf_builder import (
    KNOWN_RENDERER_LIMITATIONS,
    build_pdf_from_docx,
    compare_docx_and_pdf,
    is_pdf_renderer_available,
)


def _create_synthetic_a4_pdf(text: str = "1 Introdução\n\nTexto do trabalho acadêmico.") -> bytes:
    """Cria um PDF A4 sintético via PyMuPDF para testar o comparador de forma determinística."""
    pdf = pymupdf.open()  # type: ignore[no-untyped-call]
    # A4 em pontos: 595.28 x 841.89
    page = pdf.new_page(width=595.28, height=841.89)
    # Posição x=90pt (~3.17 cm), y=100pt (~3.52 cm) respeitando margens ABNT (3 cm)
    page.insert_text((90, 100), text, fontsize=12)
    raw: bytes = pdf.tobytes()  # type: ignore[no-untyped-call]
    pdf.close()  # type: ignore[no-untyped-call]
    return raw


def test_is_pdf_renderer_available_checks_renderer_and_binary() -> None:
    assert is_pdf_renderer_available(renderer="none") is False
    assert is_pdf_renderer_available(renderer="unknown") is False
    assert (
        is_pdf_renderer_available(renderer="libreoffice", libreoffice_binary="nao_existe_xyz")
        is False
    )
    assert is_pdf_renderer_available(renderer="docx2pdf") is False


async def test_build_pdf_declares_limitation_when_disabled_or_missing(
    template_registry: TemplateRegistry,
) -> None:
    template = template_registry.get("abnt.tcc")
    doc = AcademicDocument(id="doc-pdf-none", original_text="# Introdução\n\nTexto.")
    docx_res = build_docx(doc, template, include_pre_textual=False)

    res_none = await build_pdf_from_docx(docx_res.content, template, renderer="none")
    assert res_none.available is False
    assert res_none.content is None
    assert len(res_none.limitations) >= 1
    assert "apenas DOCX, TXT e Markdown" in res_none.limitations[0]

    res_missing = await build_pdf_from_docx(
        docx_res.content,
        template,
        renderer="libreoffice",
        libreoffice_binary="binario_inexistente_12345",
    )
    assert res_missing.available is False
    assert res_missing.content is None
    assert len(res_missing.limitations) >= 1


def test_compare_docx_and_pdf_validates_size_margins_and_breaks(
    template_registry: TemplateRegistry,
) -> None:
    template = template_registry.get("abnt.tcc")
    doc = AcademicDocument(
        id="doc-cmp",
        original_text="# Introdução\n\nParágrafo de teste.",
        metadata=DocumentMetadata(title="Título", author="Autor", year="2026"),
    )
    docx_res = build_docx(doc, template, include_pre_textual=True)
    pdf_bytes = _create_synthetic_a4_pdf()

    report = compare_docx_and_pdf(docx_res.content, pdf_bytes, template)
    assert report.page_count == 1
    assert report.page_size_matches_docx is True
    assert report.margins_respected is True
    assert report.pagination_valid is True
    assert report.pdf_non_empty_pages == 1
    assert report.limitations == KNOWN_RENDERER_LIMITATIONS
    assert any("TOC" in d for d in report.differences)


def test_compare_docx_and_pdf_detects_margin_violation_and_orphan_heading(
    template_registry: TemplateRegistry,
) -> None:
    template = template_registry.get("abnt.tcc")
    doc = AcademicDocument(id="doc-cmp-2", original_text="# Seção\n\nTexto.")
    docx_res = build_docx(doc, template, include_pre_textual=False)

    pdf = pymupdf.open()  # type: ignore[no-untyped-call]
    page = pdf.new_page(width=595.28, height=841.89)
    # Texto muito à esquerda (x=10pt ~ 0.35cm < 3cm) e título órfão no fim da página (y=780pt)
    page.insert_text((10, 120), "Texto invadindo a margem esquerda.", fontsize=12)
    page.insert_text((90, 780), "2 Seção Órfã no Fim da Página", fontsize=12)
    pdf_bytes: bytes = pdf.tobytes()  # type: ignore[no-untyped-call]
    pdf.close()  # type: ignore[no-untyped-call]

    report = compare_docx_and_pdf(docx_res.content, pdf_bytes, template)
    assert report.margins_respected is False
    assert len(report.undue_breaks) >= 1
    assert "título órfão" in report.undue_breaks[0]


@pytest.mark.integration
async def test_build_pdf_with_libreoffice_when_installed(
    template_registry: TemplateRegistry,
) -> None:
    if not is_pdf_renderer_available("libreoffice", "soffice"):
        pytest.skip("LibreOffice não instalado neste ambiente")

    template = template_registry.get("abnt.tcc")
    doc = AcademicDocument(
        id="doc-lo-real",
        original_text="# Introdução\n\nTexto acadêmico renderizado em processo isolado.",
        metadata=DocumentMetadata(title="Teste PDF", author="Autor", year="2026"),
    )
    docx_res = build_docx(doc, template, include_pre_textual=True)
    pdf_res = await build_pdf_from_docx(
        docx_res.content,
        template,
        renderer="libreoffice",
        libreoffice_binary="soffice",
    )

    assert pdf_res.available is True
    assert pdf_res.content is not None
    assert pdf_res.content.startswith(b"%PDF-")
    assert pdf_res.comparison is not None
    assert pdf_res.comparison.page_count >= 1
    assert pdf_res.comparison.page_size_matches_docx is True
    assert pdf_res.comparison.pagination_valid is True
