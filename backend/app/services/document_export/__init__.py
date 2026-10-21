"""Serviços de exportação de documentos acadêmicos (DOCX, PDF, TXT, Markdown).

Expõe o construtor DOCX com estilos e campos nativos do Word, o renderizador
de PDF em subprocesso isolado, os exportadores TXT/Markdown, a pré-visualização
estruturada e o histórico de versões exportadas.
"""

from __future__ import annotations

from app.services.document_export.docx_builder import (
    CATALOG_RECORD_RESERVATION_NOTE,
    NATIVE_CUSTOM_STYLES,
    DocxBuildResult,
    DocxInspection,
    build_docx,
    inspect_docx,
    parse_text_to_blocks,
)
from app.services.document_export.fields import (
    FieldKind,
    add_bookmark,
    add_field,
    add_numpages_field,
    add_page_field,
    add_ref_field,
    add_seq_field,
    add_styleref_field,
    add_toc_field,
    enable_update_fields_on_open,
    extract_field_instructions,
)
from app.services.document_export.pdf_builder import (
    KNOWN_RENDERER_LIMITATIONS,
    PdfBuildResult,
    PdfComparisonReport,
    build_pdf_from_docx,
    compare_docx_and_pdf,
    is_pdf_renderer_available,
)
from app.services.document_export.writer import (
    MEDIA_TYPES,
    DocumentPreview,
    ExportFormat,
    ExportHistoryStore,
    ExportRecord,
    PreviewBlock,
    PreviewTocEntry,
    export_markdown,
    export_txt,
    generate_preview,
)

__all__ = [
    "CATALOG_RECORD_RESERVATION_NOTE",
    "KNOWN_RENDERER_LIMITATIONS",
    "MEDIA_TYPES",
    "NATIVE_CUSTOM_STYLES",
    "DocumentPreview",
    "DocxBuildResult",
    "DocxInspection",
    "ExportFormat",
    "ExportHistoryStore",
    "ExportRecord",
    "FieldKind",
    "PdfBuildResult",
    "PdfComparisonReport",
    "PreviewBlock",
    "PreviewTocEntry",
    "add_bookmark",
    "add_field",
    "add_numpages_field",
    "add_page_field",
    "add_ref_field",
    "add_seq_field",
    "add_styleref_field",
    "add_toc_field",
    "build_docx",
    "build_pdf_from_docx",
    "compare_docx_and_pdf",
    "enable_update_fields_on_open",
    "export_markdown",
    "export_txt",
    "extract_field_instructions",
    "generate_preview",
    "inspect_docx",
    "is_pdf_renderer_available",
    "parse_text_to_blocks",
]
