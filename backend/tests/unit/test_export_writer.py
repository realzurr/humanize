"""Testes unitários dos exportadores TXT/Markdown, pré-visualização e histórico."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.ir.document import AcademicDocument, DocumentMetadata, DocumentRevision, PipelineStage
from app.services.academic.templates import TemplateRegistry
from app.services.document_export.docx_builder import CATALOG_RECORD_RESERVATION_NOTE
from app.services.document_export.writer import (
    ExportFormat,
    ExportHistoryStore,
    export_markdown,
    export_txt,
    generate_preview,
)

SAMPLE_TEXT = """# Introdução

Texto de introdução com dados verificáveis.

## Contextualização

> Citação direta longa com mais de três linhas para validação da exportação.

| Item | Quantidade |
|---|---|
| Amostras | 42 |

```
codigo_exemplo = True
```

REFERÊNCIAS

PEREIRA, Ana. Engenharia de software acadêmica. Curitiba: Editora UFPR, 2024.
"""


def test_export_txt_and_markdown_preserve_structure_and_reserved_catalog(
    template_registry: TemplateRegistry,
) -> None:
    template = template_registry.get("abnt.tcc")
    meta = DocumentMetadata(
        institution="UFMS",
        author="Carlos Silva",
        title="Sistema de Exportação",
        subtitle="Estudo de Caso",
        advisor="Profa. Dra. Helena",
        city="Campo Grande",
        year="2026",
    )
    doc = AcademicDocument(id="doc-w1", original_text=SAMPLE_TEXT, metadata=meta)

    txt_out = export_txt(doc, template, include_pre_textual=True).decode("utf-8")
    assert "UFMS" in txt_out
    assert "SISTEMA DE EXPORTAÇÃO: ESTUDO DE CASO" in txt_out
    assert CATALOG_RECORD_RESERVATION_NOTE in txt_out
    assert "1 Introdução" in txt_out
    assert "1.1 Contextualização" in txt_out
    assert "Amostras" in txt_out
    assert "PEREIRA, Ana" in txt_out

    md_out = export_markdown(doc, template, include_pre_textual=True).decode("utf-8")
    assert "# Sistema de Exportação: Estudo de Caso" in md_out
    assert "# 1 Introdução" in md_out
    assert "## 1.1 Contextualização" in md_out
    assert "> Citação direta longa" in md_out
    assert "| Item | Quantidade |" in md_out
    assert "```" in md_out
    assert "- PEREIRA, Ana" in md_out


def test_generate_preview_returns_toc_margins_and_blocks(
    template_registry: TemplateRegistry,
) -> None:
    template = template_registry.get("abnt.tcc")
    doc = AcademicDocument(
        id="doc-prev",
        original_text=SAMPLE_TEXT,
        metadata=DocumentMetadata(title="Prévia Acadêmica"),
    )
    preview = generate_preview(doc, template)

    assert preview.document_id == "doc-prev"
    assert preview.title == "Prévia Acadêmica"
    assert preview.font == "Times New Roman"
    assert preview.margins_anverso_cm == {"top": 3.0, "bottom": 2.0, "left": 3.0, "right": 2.0}
    assert preview.margins_verso_cm == {"top": 3.0, "bottom": 2.0, "left": 2.0, "right": 3.0}
    assert len(preview.toc_entries) >= 2
    assert preview.toc_entries[0].number == "1"
    assert preview.toc_entries[0].title == "Introdução"
    assert preview.toc_entries[1].number == "1.1"
    assert any(b.style == "Citacao Longa" for b in preview.blocks)
    assert any(b.style == "Referencia" for b in preview.blocks)


def test_export_history_store_versions_and_retention(tmp_path: Path) -> None:
    store = ExportHistoryStore(tmp_path / "exports", retention_days=7)
    doc = AcademicDocument(id="doc-hist", original_text="Texto original imutável")
    rev = DocumentRevision(
        id="rev-1",
        stage=PipelineStage.EXPORT,
        text="Texto revisado",
    )
    doc_rev = doc.with_revision(rev)
    store.register_document(doc_rev)

    rec1 = store.record_export(
        document_id="doc-hist",
        revision_id="rev-1",
        fmt=ExportFormat.TXT,
        content=b"versao 1",
        template_id="abnt.tcc",
    )
    rec2 = store.record_export(
        document_id="doc-hist",
        revision_id="rev-1",
        fmt=ExportFormat.TXT,
        content=b"versao 2",
        template_id="abnt.tcc",
    )

    assert rec1.version_number == 1
    assert rec2.version_number == 2
    assert store.read_bytes(rec1.id) == b"versao 1"
    assert store.read_bytes(rec2.id) == b"versao 2"
    assert len(store.list_records("doc-hist")) == 2

    resumo = store.summary_for_document("doc-hist")
    assert resumo["original_immutable"] is True
    assert len(resumo["revisions"]) == 1
    assert len(resumo["exports"]) == 2

    # Testa expurgo por retenção
    futuro = datetime.now(UTC) + timedelta(days=10)
    removidos = store.prune_expired(now=futuro)
    assert removidos == 2
    assert store.get(rec1.id) is None
    assert store.read_bytes(rec1.id) is None
