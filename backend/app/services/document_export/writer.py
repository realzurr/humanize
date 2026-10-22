"""Exportadores em texto plano (TXT), Markdown, pré-visualização e histórico.

Complementa a geração de DOCX/PDF com saídas determinísticas em TXT e Markdown,
pré-visualização estruturada para a interface e armazenamento do histórico de
versões exportadas com hash SHA-256 (`ADR-0012`).
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.ir.blocks import Block, BlockKind
from app.ir.document import AcademicDocument
from app.services.academic.numbering import progressive_numbers
from app.services.academic.pagination import PageSide, resolve_margins
from app.services.academic.structure import _HEADING_MD_RE, _HEADING_NUM_RE
from app.services.academic.template_model import Margens, Pagina, Template
from app.services.document_export.docx_builder import (
    CATALOG_RECORD_RESERVATION_NOTE,
    DocxInspection,
    parse_text_to_blocks,
)
from app.services.document_export.pdf_builder import PdfComparisonReport

_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_.-]+")


class ExportFormat(StrEnum):
    """Formatos suportados de exportação."""

    DOCX = "docx"
    PDF = "pdf"
    TXT = "txt"
    MARKDOWN = "md"


MEDIA_TYPES: dict[ExportFormat, str] = {
    ExportFormat.DOCX: ("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ExportFormat.PDF: "application/pdf",
    ExportFormat.TXT: "text/plain; charset=utf-8",
    ExportFormat.MARKDOWN: "text/markdown; charset=utf-8",
}


class PreviewTocEntry(BaseModel):
    """Item do sumário na pré-visualização."""

    model_config = ConfigDict(frozen=True)

    number: str
    title: str
    level: int


class PreviewBlock(BaseModel):
    """Bloco renderizável na pré-visualização da interface."""

    model_config = ConfigDict(frozen=True)

    id: str
    kind: str
    style: str
    text: str
    level: int = 1


class DocumentPreview(BaseModel):
    """Pré-visualização estruturada do documento antes ou depois da exportação."""

    model_config = ConfigDict(frozen=True)

    document_id: str
    title: str
    template_id: str
    font: str
    font_size_pt: float
    line_spacing: float
    margins_anverso_cm: dict[str, float]
    margins_verso_cm: dict[str, float]
    toc_entries: tuple[PreviewTocEntry, ...]
    blocks: tuple[PreviewBlock, ...]
    revision_count: int
    current_revision_id: str | None


class ExportRecord(BaseModel):
    """Metadados de uma versão exportada no histórico."""

    model_config = ConfigDict(frozen=True)

    id: str
    document_id: str
    revision_id: str | None
    version_number: int
    format: ExportFormat
    filename: str
    sha256: str
    size_bytes: int
    template_id: str
    institution_id: str | None = None
    owner_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    warnings: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    docx_inspection: DocxInspection | None = None
    pdf_comparison: PdfComparisonReport | None = None


def _clean_heading_title(raw: str) -> str:
    txt = raw.strip()
    m_md = _HEADING_MD_RE.match(txt)
    if m_md:
        txt = m_md.group(2).strip()
    m_num = _HEADING_NUM_RE.match(txt)
    if m_num:
        txt = m_num.group(2).strip()
    return txt


def _compute_heading_numbers(
    blocks: tuple[Block, ...],
    start_at: int = 1,
) -> dict[int, str]:
    indices: list[int] = []
    niveis: list[int] = []
    for idx, b in enumerate(blocks):
        if b.kind is BlockKind.HEADING and not b.attributes.get("unnumbered", False):
            indices.append(idx)
            niveis.append(max(1, min(b.level, 4)))
    numeros = progressive_numbers(niveis, start_at=start_at)
    return dict(zip(indices, numeros, strict=False))


def export_txt(
    document: AcademicDocument,
    template: Template,
    *,
    include_pre_textual: bool = True,
) -> bytes:
    """Exporta o documento em formato TXT estruturado (UTF-8)."""
    blocos = document.blocks if document.blocks else parse_text_to_blocks(document.current_text())
    start_at = template.sections.start_at if template.sections is not None else 1
    mapa_num = _compute_heading_numbers(blocos, start_at=start_at)

    linhas: list[str] = []
    meta = document.metadata
    if include_pre_textual:
        if meta.institution:
            linhas.append(meta.institution.upper())
        if meta.author:
            linhas.append(meta.author.upper())
        if meta.title:
            titulo = f"{meta.title}: {meta.subtitle}" if meta.subtitle else meta.title
            linhas.append(titulo.upper())
        if any(el.kind == "catalog_record" for el in template.elements):
            linhas.append("")
            linhas.append(CATALOG_RECORD_RESERVATION_NOTE)
        linhas.append("")

    for idx, bloco in enumerate(blocos):
        if bloco.kind is BlockKind.HEADING:
            titulo = _clean_heading_title(bloco.plain_text)
            if bloco.attributes.get("unnumbered", False):
                linhas.append(titulo.upper())
            else:
                num = str(bloco.attributes.get("number") or mapa_num.get(idx, ""))
                linhas.append(f"{num} {titulo}".strip())
            linhas.append("")
        elif bloco.kind is BlockKind.REFERENCES:
            linhas.append("REFERÊNCIAS")
            linhas.append("")
            for child in bloco.children:
                linhas.append(child.plain_text.strip())
                linhas.append("")
        elif bloco.kind is BlockKind.TABLE and bloco.table is not None:
            if bloco.table.caption:
                linhas.append(f"Tabela — {bloco.table.caption}")
            for row in bloco.table.rows:
                linhas.append(" | ".join(row))
            if bloco.table.source:
                linhas.append(f"Fonte: {bloco.table.source}")
            linhas.append("")
        elif bloco.kind is BlockKind.CATALOG_RECORD:
            linhas.append(CATALOG_RECORD_RESERVATION_NOTE)
            linhas.append("")
        else:
            texto = bloco.plain_text.strip()
            if texto:
                linhas.append(texto)
                linhas.append("")

    conteudo = "\n".join(linhas).strip() + "\n"
    return conteudo.encode("utf-8")


def export_markdown(
    document: AcademicDocument,
    template: Template,
    *,
    include_pre_textual: bool = True,
) -> bytes:
    """Exporta o documento em formato Markdown estruturado (UTF-8)."""
    blocos = document.blocks if document.blocks else parse_text_to_blocks(document.current_text())
    start_at = template.sections.start_at if template.sections is not None else 1
    mapa_num = _compute_heading_numbers(blocos, start_at=start_at)

    linhas: list[str] = []
    meta = document.metadata
    if include_pre_textual:
        if meta.title:
            titulo = f"{meta.title}: {meta.subtitle}" if meta.subtitle else meta.title
            linhas.append(f"# {titulo}")
            linhas.append("")
        if meta.author:
            linhas.append(f"**Autor(a):** {meta.author}")
        if meta.institution:
            linhas.append(f"**Instituição:** {meta.institution}")
        if meta.advisor:
            linhas.append(f"**Orientador(a):** {meta.advisor}")
        if meta.city or meta.year:
            linhas.append(f"**Local/Ano:** {' — '.join(p for p in (meta.city, meta.year) if p)}")
        if any(el.kind == "catalog_record" for el in template.elements):
            linhas.append("")
            linhas.append(f"> {CATALOG_RECORD_RESERVATION_NOTE}")
        linhas.append("")

    for idx, bloco in enumerate(blocos):
        if bloco.kind is BlockKind.HEADING:
            titulo = _clean_heading_title(bloco.plain_text)
            nivel = max(1, min(bloco.level, 6))
            hashes = "#" * nivel
            if bloco.attributes.get("unnumbered", False):
                linhas.append(f"{hashes} {titulo.upper()}")
            else:
                num = str(bloco.attributes.get("number") or mapa_num.get(idx, ""))
                linhas.append(f"{hashes} {num} {titulo}".strip())
            linhas.append("")
        elif bloco.kind is BlockKind.REFERENCES:
            linhas.append("## REFERÊNCIAS")
            linhas.append("")
            for child in bloco.children:
                linhas.append(f"- {child.plain_text.strip()}")
            linhas.append("")
        elif bloco.kind is BlockKind.REFERENCE_ITEM:
            linhas.append(f"- {bloco.plain_text.strip()}")
            linhas.append("")
        elif bloco.kind is BlockKind.QUOTE_LONG:
            linhas.append(f"> {bloco.plain_text.strip()}")
            linhas.append("")
        elif bloco.kind is BlockKind.CODE_BLOCK:
            linhas.append("```")
            linhas.append(bloco.plain_text)
            linhas.append("```")
            linhas.append("")
        elif bloco.kind is BlockKind.TABLE and bloco.table is not None and bloco.table.rows:
            if bloco.table.caption:
                linhas.append(f"**Tabela — {bloco.table.caption}**")
                linhas.append("")
            header = bloco.table.rows[0]
            linhas.append("| " + " | ".join(header) + " |")
            linhas.append("| " + " | ".join("---" for _ in header) + " |")
            for row in bloco.table.rows[1:]:
                linhas.append("| " + " | ".join(row) + " |")
            if bloco.table.source:
                linhas.append("")
                linhas.append(f"*Fonte: {bloco.table.source}*")
            linhas.append("")
        elif bloco.kind is BlockKind.CATALOG_RECORD:
            linhas.append(f"> {CATALOG_RECORD_RESERVATION_NOTE}")
            linhas.append("")
        else:
            texto = bloco.plain_text.strip()
            if texto:
                linhas.append(texto)
                linhas.append("")

    conteudo = "\n".join(linhas).strip() + "\n"
    return conteudo.encode("utf-8")


def generate_preview(document: AcademicDocument, template: Template) -> DocumentPreview:
    """Gera a estrutura de pré-visualização (sumário, estilos e blocos) para a UI."""
    blocos = document.blocks if document.blocks else parse_text_to_blocks(document.current_text())
    start_at = template.sections.start_at if template.sections is not None else 1
    mapa_num = _compute_heading_numbers(blocos, start_at=start_at)

    page = template.page or Pagina(
        size="A4",
        mirror=True,
        margins_cm=Margens(top_cm=3.0, bottom_cm=2.0, left_cm=3.0, right_cm=2.0),
    )
    anverso = resolve_margins(page, PageSide.ANVERSO)
    verso = resolve_margins(page, PageSide.VERSO)

    font_name = template.typography.font if template.typography else "Times New Roman"
    font_size = template.typography.size_pt if template.typography else 12.0
    line_spacing = template.typography.line_spacing if template.typography else 1.5

    toc_entries: list[PreviewTocEntry] = []
    preview_blocks: list[PreviewBlock] = []

    for idx, bloco in enumerate(blocos):
        if bloco.kind is BlockKind.HEADING:
            titulo = _clean_heading_title(bloco.plain_text)
            sem_ind = bool(bloco.attributes.get("unnumbered", False))
            if sem_ind:
                toc_entries.append(PreviewTocEntry(number="", title=titulo.upper(), level=1))
                preview_blocks.append(
                    PreviewBlock(
                        id=bloco.id,
                        kind="heading",
                        style="Sem Indicativo",
                        text=titulo.upper(),
                        level=1,
                    )
                )
            else:
                nivel = max(1, min(bloco.level, 4))
                num = str(bloco.attributes.get("number") or mapa_num.get(idx, ""))
                toc_entries.append(PreviewTocEntry(number=num, title=titulo, level=nivel))
                preview_blocks.append(
                    PreviewBlock(
                        id=bloco.id,
                        kind="heading",
                        style=f"Heading {nivel}",
                        text=f"{num} {titulo}".strip(),
                        level=nivel,
                    )
                )
        elif bloco.kind is BlockKind.REFERENCES:
            toc_entries.append(PreviewTocEntry(number="", title="REFERÊNCIAS", level=1))
            preview_blocks.append(
                PreviewBlock(
                    id=bloco.id,
                    kind="references",
                    style="Sem Indicativo",
                    text="REFERÊNCIAS",
                    level=1,
                )
            )
        elif bloco.kind is BlockKind.REFERENCE_ITEM:
            preview_blocks.append(
                PreviewBlock(
                    id=bloco.id,
                    kind="reference_item",
                    style="Referencia",
                    text=bloco.plain_text,
                )
            )
        elif bloco.kind is BlockKind.QUOTE_LONG:
            preview_blocks.append(
                PreviewBlock(
                    id=bloco.id,
                    kind="quote_long",
                    style="Citacao Longa",
                    text=bloco.plain_text,
                )
            )
        elif bloco.kind is BlockKind.TABLE and bloco.table is not None:
            resumo_tabela = "\n".join(" | ".join(r) for r in bloco.table.rows)
            preview_blocks.append(
                PreviewBlock(
                    id=bloco.id,
                    kind="table",
                    style="Table Grid",
                    text=resumo_tabela,
                )
            )
        else:
            preview_blocks.append(
                PreviewBlock(
                    id=bloco.id,
                    kind=str(bloco.kind),
                    style="Normal",
                    text=bloco.plain_text,
                )
            )

    return DocumentPreview(
        document_id=document.id,
        title=document.metadata.title or "Documento sem título",
        template_id=template.id,
        font=font_name,
        font_size_pt=font_size,
        line_spacing=line_spacing,
        margins_anverso_cm={
            "top": anverso.top_cm,
            "bottom": anverso.bottom_cm,
            "left": anverso.left_cm,
            "right": anverso.right_cm,
        },
        margins_verso_cm={
            "top": verso.top_cm,
            "bottom": verso.bottom_cm,
            "left": verso.left_cm,
            "right": verso.right_cm,
        },
        toc_entries=tuple(toc_entries),
        blocks=tuple(preview_blocks),
        revision_count=len(document.revisions),
        current_revision_id=document.current_revision_id,
    )


class ExportHistoryStore:
    """Armazenamento de arquivos exportados e histórico de versões por documento."""

    def __init__(self, export_dir: Path, *, retention_days: int = 30) -> None:
        self._export_dir = export_dir.resolve()
        self._retention_days = retention_days
        self._records: dict[str, ExportRecord] = {}
        self._documents: dict[str, AcademicDocument] = {}

    def register_document(self, document: AcademicDocument) -> None:
        """Registra ou atualiza o documento e seu histórico de revisões."""
        self._documents[document.id] = document

    def get_document(
        self, document_id: str, owner_id: str | None = None
    ) -> AcademicDocument | None:
        documento = self._documents.get(document_id)
        if documento is None:
            return None
        return documento if documento.owner_id == owner_id else None

    def record_export(
        self,
        *,
        document_id: str,
        revision_id: str | None,
        fmt: ExportFormat,
        content: bytes,
        template_id: str,
        institution_id: str | None = None,
        owner_id: str | None = None,
        warnings: tuple[str, ...] = (),
        limitations: tuple[str, ...] = (),
        docx_inspection: DocxInspection | None = None,
        pdf_comparison: PdfComparisonReport | None = None,
    ) -> ExportRecord:
        """Persiste o arquivo exportado em ``export_dir`` e registra a versão."""
        self._export_dir.mkdir(parents=True, exist_ok=True)
        export_id = f"exp_{uuid.uuid4().hex[:12]}"
        safe_doc = _SAFE_ID_RE.sub("_", document_id).strip("._") or "documento"

        versao = (
            sum(
                1
                for r in self._records.values()
                if r.document_id == document_id and r.format is fmt
            )
            + 1
        )
        filename = f"{safe_doc}_v{versao}_{export_id}.{fmt.value}"
        target_path = (self._export_dir / filename).resolve()
        if not target_path.is_relative_to(self._export_dir):
            raise ValueError("caminho de exportação fora do diretório permitido")

        target_path.write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()

        record = ExportRecord(
            id=export_id,
            document_id=document_id,
            revision_id=revision_id,
            version_number=versao,
            format=fmt,
            filename=filename,
            sha256=digest,
            size_bytes=len(content),
            template_id=template_id,
            institution_id=institution_id,
            owner_id=owner_id,
            warnings=warnings,
            limitations=limitations,
            docx_inspection=docx_inspection,
            pdf_comparison=pdf_comparison,
        )
        self._records[export_id] = record
        return record

    def get(self, export_id: str, owner_id: str | None = None) -> ExportRecord | None:
        record = self._records.get(export_id)
        if record is None:
            return None
        return record if record.owner_id == owner_id else None

    def read_bytes(self, export_id: str, owner_id: str | None = None) -> bytes | None:
        record = self.get(export_id, owner_id)
        if record is None:
            return None
        path = (self._export_dir / record.filename).resolve()
        if not path.is_relative_to(self._export_dir) or not path.exists():
            return None
        return path.read_bytes()

    def list_records(
        self,
        document_id: str | None = None,
        owner_id: str | None = None,
    ) -> list[ExportRecord]:
        itens = [r for r in self._records.values() if r.owner_id == owner_id]
        if document_id is not None:
            itens = [r for r in itens if r.document_id == document_id]
        return sorted(itens, key=lambda r: r.created_at, reverse=True)

    def prune_expired(self, *, now: datetime | None = None) -> int:
        """Remove exportações vencidas conforme a política de retenção (`ADR-0012`)."""
        referencia = now or datetime.now(UTC)
        limite = referencia - timedelta(days=self._retention_days)
        removidos = 0
        for exp_id, record in list(self._records.items()):
            if record.created_at < limite:
                caminho = (self._export_dir / record.filename).resolve()
                if caminho.is_relative_to(self._export_dir) and caminho.exists():
                    caminho.unlink()
                del self._records[exp_id]
                removidos += 1
        return removidos

    def summary_for_document(self, document_id: str, owner_id: str | None = None) -> dict[str, Any]:
        """Devolve o histórico combinado de revisões do IR e de arquivos exportados."""
        doc = self.get_document(document_id, owner_id)
        revisoes = (
            [
                {
                    "id": rev.id,
                    "stage": str(rev.stage),
                    "created_at": rev.created_at.isoformat(),
                    "parent_id": rev.parent_id,
                    "transformations": len(rev.transformations),
                }
                for rev in doc.history()
            ]
            if doc is not None
            else []
        )
        exports = [r.model_dump(mode="json") for r in self.list_records(document_id, owner_id)]
        return {
            "document_id": document_id,
            "original_immutable": True,
            "revisions": revisoes,
            "exports": exports,
        }
