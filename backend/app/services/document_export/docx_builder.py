"""Construtor de documentos DOCX com estilos e campos nativos do Word.

Gera arquivos ``.docx`` editáveis no Microsoft Word e no LibreOffice Writer,
aplicando as regras parametrizadas do template ABNT resolvido (margens,
tipografia, títulos hierárquicos, citações longas, legendas, fontes e
referências) sem recorrer a alinhamento visual simulado por espaços ou
tabulações repetidas (`ADR-0005` e `ADR-0012`).
"""

from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Callable
from typing import TYPE_CHECKING, cast

import docx
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from pydantic import BaseModel, ConfigDict

from app.ir.blocks import PAGE_BREAK_BLOCKS, Block, BlockKind, TableData
from app.ir.document import AcademicDocument, DocumentMetadata, PipelineStage, Transformation
from app.ir.spans import InlineSpan, SpanKind
from app.services.academic.numbering import progressive_numbers
from app.services.academic.pagination import PageSide, page_number_position, resolve_margins
from app.services.academic.structure import _HEADING_MD_RE, _HEADING_NUM_RE, detect_structure
from app.services.academic.styles import style_for_kind, style_for_level
from app.services.academic.template_model import Estilo, Margens, Pagina, Template, Tipografia
from app.services.document_export.fields import (
    add_bookmark,
    add_page_field,
    add_ref_field,
    add_seq_field,
    add_toc_field,
    enable_update_fields_on_open,
    extract_field_instructions,
)
from app.services.references.nbr6023 import format_reference
from app.services.references.parser import _REFERENCES_HEADING_RE, parse_references

if TYPE_CHECKING:
    from docx.document import Document as DocumentObject
    from docx.styles.style import _ParagraphStyle
    from docx.text.paragraph import Paragraph
    from docx.text.run import Run

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

#: Conversão exata de twips (1/20 de ponto) para centímetros (1 pol = 1440 twips = 2.54 cm).
_TWIPS_PER_CM = 1440.0 / 2.54

#: Mapa de alinhamento textual para constantes do python-docx.
_ALIGN_MAP: dict[str, WD_ALIGN_PARAGRAPH] = {
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
}

#: Nomes canônicos dos estilos nativos e customizados criados no DOCX.
NATIVE_CUSTOM_STYLES: dict[str, str] = {
    "citacao_longa": "Citacao Longa",
    "legenda": "Legenda",
    "fonte": "Fonte",
    "referencia": "Referencia",
    "sem_indicativo": "Sem Indicativo",
    "nota_rodape": "Nota Rodape",
    "codigo": "Codigo",
}

_MULTI_SPACE_RE = re.compile(r" {2,}")
_MULTI_TAB_RE = re.compile(r"\t+")
_REF_PLACEHOLDER_RE = re.compile(r"\[\[REF:([A-Za-z0-9_-]+)\]\]")

#: Nota padrão para o espaço reservado da ficha catalográfica (nunca fictícia).
CATALOG_RECORD_RESERVATION_NOTE = (
    "[Espaço reservado para a Ficha Catalográfica — emitida pela biblioteca da "
    "instituição. Nenhum dado catalográfico fictício é gerado pelo sistema.]"
)


class DocxInspection(BaseModel):
    """Inspeção estrutural de ``styles.xml``, ``document.xml`` e ``settings.xml``."""

    model_config = ConfigDict(frozen=True)

    style_names: tuple[str, ...]
    paragraph_styles_used: tuple[str, ...]
    fields: tuple[str, ...]
    has_toc_field: bool
    has_page_field: bool
    has_update_fields: bool
    has_alignment_simulation: bool
    catalog_record_reserved: bool
    table_count: int
    heading_count: int
    page_width_cm: float
    page_height_cm: float
    margins_cm: dict[str, float]


class DocxBuildResult(BaseModel):
    """Resultado da construção de um arquivo DOCX."""

    model_config = ConfigDict(frozen=True)

    content: bytes
    transformations: tuple[Transformation, ...]
    warnings: tuple[str, ...]
    inspection: DocxInspection


def _sanitize_text(text: str) -> str:
    """Remove espaços repetidos e tabulações para impedir simulação visual de layout."""
    sem_tabs = _MULTI_TAB_RE.sub(" ", text)
    return _MULTI_SPACE_RE.sub(" ", sem_tabs).strip()


def _default_typography(template: Template) -> Tipografia:
    if template.typography is not None:
        return template.typography
    return Tipografia(
        font="Times New Roman",
        size_pt=12.0,
        small_size_pt=10.0,
        line_spacing=1.5,
        paragraph_spacing_pt=0.0,
        indent_cm=1.25,
        alignment="justify",
    )


def _default_page(template: Template) -> Pagina:
    if template.page is not None:
        return template.page
    return Pagina(
        size="A4",
        mirror=True,
        margins_cm=Margens(top_cm=3.0, bottom_cm=2.0, left_cm=3.0, right_cm=2.0),
    )


def _get_or_create_paragraph_style(doc: DocumentObject, style_name: str) -> _ParagraphStyle:
    styles = doc.styles
    if style_name in styles:
        return cast("_ParagraphStyle", styles[style_name])
    return cast("_ParagraphStyle", styles.add_style(style_name, WD_STYLE_TYPE.PARAGRAPH))


def _apply_estilo_to_word_style(
    word_style: _ParagraphStyle,
    estilo: Estilo,
    typo: Tipografia,
    *,
    is_normal: bool = False,
) -> None:
    font = word_style.font
    font.name = typo.font
    tamanho = estilo.font_size_pt if estilo.font_size_pt is not None else typo.size_pt
    font.size = Pt(tamanho)
    font.bold = estilo.bold
    font.italic = estilo.italic

    pf = word_style.paragraph_format
    alinhamento_chave = typo.alignment if is_normal else estilo.alignment
    pf.alignment = _ALIGN_MAP.get(alinhamento_chave, WD_ALIGN_PARAGRAPH.LEFT)
    pf.space_before = Pt(estilo.spacing_before_pt)
    pf.space_after = Pt(typo.paragraph_spacing_pt if is_normal else estilo.spacing_after_pt)
    entrelinha = estilo.line_spacing if estilo.line_spacing is not None else typo.line_spacing
    pf.line_spacing = entrelinha
    pf.keep_with_next = estilo.keep_with_next

    if is_normal:
        pf.first_line_indent = Cm(typo.indent_cm)
        pf.left_indent = Cm(0.0)
    elif estilo.indent_cm is not None:
        pf.left_indent = Cm(estilo.indent_cm)
        pf.first_line_indent = Cm(0.0)
    else:
        pf.first_line_indent = Cm(0.0)


def _configure_styles(doc: DocumentObject, template: Template) -> None:
    """Configura estilos nativos do Word a partir do template parametrizado."""
    typo = _default_typography(template)
    normal_style = _get_or_create_paragraph_style(doc, "Normal")
    _apply_estilo_to_word_style(
        normal_style, Estilo(alignment=typo.alignment), typo, is_normal=True
    )

    for nivel in (1, 2, 3, 4):
        estilo_titulo = style_for_level(template.styles, min(nivel, 3))
        heading_style = _get_or_create_paragraph_style(doc, f"Heading {nivel}")
        _apply_estilo_to_word_style(heading_style, estilo_titulo, typo)

    # Estilos específicos ABNT (citação longa, legenda, fonte, referência, título sem indicativo)
    defaults_especiais: dict[str, Estilo] = {
        "citacao_longa": Estilo(
            font_size_pt=typo.small_size_pt,
            line_spacing=1.0,
            alignment="justify",
            indent_cm=4.0,
            spacing_before_pt=6.0,
            spacing_after_pt=6.0,
        ),
        "legenda": Estilo(
            font_size_pt=typo.small_size_pt,
            line_spacing=1.0,
            alignment="left",
            spacing_before_pt=6.0,
            spacing_after_pt=3.0,
            keep_with_next=True,
        ),
        "fonte": Estilo(
            font_size_pt=typo.small_size_pt,
            line_spacing=1.0,
            alignment="left",
            spacing_before_pt=2.0,
            spacing_after_pt=6.0,
        ),
        "referencia": Estilo(
            font_size_pt=typo.size_pt,
            line_spacing=1.0,
            alignment="left",
            spacing_before_pt=0.0,
            spacing_after_pt=6.0,
        ),
        "sem_indicativo": Estilo(
            font_size_pt=typo.size_pt,
            bold=True,
            uppercase=True,
            alignment="center",
            spacing_before_pt=12.0,
            spacing_after_pt=12.0,
            keep_with_next=True,
        ),
        "nota_rodape": Estilo(
            font_size_pt=typo.small_size_pt,
            line_spacing=1.0,
            alignment="justify",
        ),
    }

    for chave, nome_word in NATIVE_CUSTOM_STYLES.items():
        if chave == "codigo":
            estilo_code = _get_or_create_paragraph_style(doc, nome_word)
            estilo_code.font.name = "Courier New"
            estilo_code.font.size = Pt(typo.small_size_pt)
            estilo_code.paragraph_format.line_spacing = 1.0
            estilo_code.paragraph_format.first_line_indent = Cm(0.0)
            estilo_code.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            continue
        declarado = template.styles.get(chave)
        efetivo = declarado if declarado is not None else style_for_kind(defaults_especiais, chave)
        word_st = _get_or_create_paragraph_style(doc, nome_word)
        _apply_estilo_to_word_style(word_st, efetivo, typo)


def _configure_page_and_headers(doc: DocumentObject, template: Template) -> None:
    """Configura tamanho de página A4, margens parametrizadas e cabeçalhos com ``PAGE``."""
    page = _default_page(template)
    typo = _default_typography(template)
    margens_anverso = resolve_margins(page, PageSide.ANVERSO)

    section = doc.sections[0]
    if page.size.upper() == "A4":
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)

    section.top_margin = Cm(margens_anverso.top_cm)
    section.bottom_margin = Cm(margens_anverso.bottom_cm)
    section.left_margin = Cm(margens_anverso.left_cm)
    section.right_margin = Cm(margens_anverso.right_cm)
    section.gutter = Cm(page.gutter_cm)

    # Omite numeração visível na primeira página (capa / pré-textual inicial).
    section.different_first_page_header_footer = not page.numbering.number_pre_textual

    pos_anverso = page_number_position(page, PageSide.ANVERSO)
    header_para = section.header.paragraphs[0]
    header_para.style = doc.styles["Normal"]
    header_para.paragraph_format.first_line_indent = Cm(0.0)
    header_para.alignment = (
        WD_ALIGN_PARAGRAPH.LEFT if pos_anverso == "top_left" else WD_ALIGN_PARAGRAPH.RIGHT
    )
    add_page_field(header_para)
    for run in header_para.runs:
        run.font.name = typo.font
        run.font.size = Pt(typo.small_size_pt)

    if page.mirror:
        doc.settings.odd_and_even_pages_header_footer = True
        settings_el = doc.settings.element
        if settings_el.find(qn("w:mirrorMargins")) is None:
            settings_el.append(OxmlElement("w:mirrorMargins"))

        pos_verso = page_number_position(page, PageSide.VERSO)
        even_para = section.even_page_header.paragraphs[0]
        even_para.style = doc.styles["Normal"]
        even_para.paragraph_format.first_line_indent = Cm(0.0)
        even_para.alignment = (
            WD_ALIGN_PARAGRAPH.LEFT if pos_verso == "top_left" else WD_ALIGN_PARAGRAPH.RIGHT
        )
        add_page_field(even_para)
        for run in even_para.runs:
            run.font.name = typo.font
            run.font.size = Pt(typo.small_size_pt)


def _add_page_break(doc: DocumentObject) -> Paragraph:
    p = doc.add_paragraph()
    p.add_run().add_break(WD_BREAK.PAGE)
    return p


def _add_centered_line(doc: DocumentObject, text: str, *, bold: bool = False) -> Paragraph:
    p = doc.add_paragraph(style="Normal")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0.0)
    run = p.add_run(_sanitize_text(text))
    run.bold = bold
    return p


def _render_pre_textual_from_metadata(
    doc: DocumentObject,
    metadata: DocumentMetadata,
    template: Template,
    existing_kinds: set[BlockKind],
) -> list[Transformation]:
    """Gera capa, folha de rosto, ficha catalográfica reservada, resumo e sumário."""
    transformacoes: list[Transformation] = []
    element_kinds = {el.kind for el in template.elements}

    # 1. Capa (se requerida pelo template ou se metadados informados)
    if ("cover" in element_kinds or metadata.title) and BlockKind.COVER not in existing_kinds:
        if metadata.institution:
            _add_centered_line(doc, metadata.institution.upper(), bold=True)
        if metadata.academic_unit:
            _add_centered_line(doc, metadata.academic_unit.upper())
        if metadata.author:
            _add_centered_line(doc, metadata.author.upper(), bold=True)

        titulo_completo = metadata.title or "TÍTULO DO TRABALHO"
        if metadata.subtitle:
            titulo_completo = f"{titulo_completo}: {metadata.subtitle}"
        p_title = _add_centered_line(doc, titulo_completo.upper(), bold=True)
        p_title.paragraph_format.space_before = Pt(72.0)
        p_title.paragraph_format.space_after = Pt(72.0)

        rodape_local = " — ".join(p for p in (metadata.city, metadata.year) if p)
        if rodape_local:
            _add_centered_line(doc, rodape_local)

        transformacoes.append(
            Transformation(
                stage=PipelineStage.EXPORT,
                rule_id="export.docx.cover",
                description="Capa gerada com alinhamento nativo de parágrafo.",
            )
        )

    # 2. Folha de rosto
    if "title_page" in element_kinds and BlockKind.TITLE_PAGE not in existing_kinds:
        _add_page_break(doc)
        if metadata.author:
            _add_centered_line(doc, metadata.author.upper(), bold=True)
        titulo_completo = metadata.title or "TÍTULO DO TRABALHO"
        if metadata.subtitle:
            titulo_completo = f"{titulo_completo}: {metadata.subtitle}"
        _add_centered_line(doc, titulo_completo.upper(), bold=True)

        natureza_partes: list[str] = []
        if metadata.academic_objective:
            natureza_partes.append(metadata.academic_objective)
        elif metadata.nature:
            natureza_partes.append(f" Trabalho acadêmico ({metadata.nature.value})")
        if metadata.advisor:
            natureza_partes.append(f"Orientador(a): {metadata.advisor}.")
        if metadata.co_advisor:
            natureza_partes.append(f"Coorientador(a): {metadata.co_advisor}.")
        if natureza_partes:
            p_nat = doc.add_paragraph(
                _sanitize_text(" ".join(natureza_partes)),
                style="Citacao Longa",
            )
            p_nat.paragraph_format.left_indent = Cm(8.0)

        rodape_local = " — ".join(p for p in (metadata.city, metadata.year) if p)
        if rodape_local:
            _add_centered_line(doc, rodape_local)

    # 3. Ficha catalográfica — SEMPRE reservada, nunca fictícia (ADR-0015 / regra 5)
    if "catalog_record" in element_kinds and BlockKind.CATALOG_RECORD not in existing_kinds:
        _add_page_break(doc)
        p_cat = doc.add_paragraph(style="Fonte")
        p_cat.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cat.paragraph_format.space_before = Pt(120.0)
        p_cat.add_run(CATALOG_RECORD_RESERVATION_NOTE)
        transformacoes.append(
            Transformation(
                stage=PipelineStage.EXPORT,
                rule_id="export.docx.catalog_record_reserved",
                description="Campo de ficha catalográfica reservado sem dados fictícios.",
            )
        )

    # 4. Sumário automático (campo TOC real do Word)
    if "table_of_contents" in element_kinds and BlockKind.TABLE_OF_CONTENTS not in existing_kinds:
        _add_page_break(doc)
        doc.add_paragraph("SUMÁRIO", style="Sem Indicativo")
        p_toc = doc.add_paragraph(style="Normal")
        p_toc.paragraph_format.first_line_indent = Cm(0.0)
        add_toc_field(p_toc, levels="1-3")
        _add_page_break(doc)
        transformacoes.append(
            Transformation(
                stage=PipelineStage.EXPORT,
                rule_id="export.docx.toc_field",
                description="Sumário inserido como campo dinâmico TOC real do Word.",
            )
        )

    return transformacoes


def parse_text_to_blocks(text: str) -> tuple[Block, ...]:
    """Converte texto plano/Markdown em sequência estruturada de :class:`Block`.

    Preserva blocos de código cercados, tabelas pipe-delimited, títulos com e
    sem indicativo, citações longas, legendas, fontes e referências.
    """
    linhas = text.splitlines()
    secoes_por_linha = {s.line: s for s in detect_structure(text)}

    blocos: list[Block] = []
    indice_bloco = 0

    def _novo_id() -> str:
        nonlocal indice_bloco
        indice_bloco += 1
        return f"b{indice_bloco:04d}"

    em_codigo = False
    buffer_codigo: list[str] = []
    buffer_tabela: list[list[str]] = []
    em_referencias = False
    linhas_referencia: list[str] = []

    def _descarregar_tabela() -> None:
        nonlocal buffer_tabela
        if not buffer_tabela:
            return
        colunas = max(len(r) for r in buffer_tabela)
        linhas_norm = tuple(
            tuple(r[i] if i < len(r) else "" for i in range(colunas)) for r in buffer_tabela
        )
        blocos.append(
            Block(
                id=_novo_id(),
                kind=BlockKind.TABLE,
                table=TableData(
                    rows=linhas_norm,
                    column_count=colunas,
                    caption="Tabela de dados",
                ),
            )
        )
        buffer_tabela = []

    for num_linha, linha_bruta in enumerate(linhas):
        stripped = linha_bruta.strip()

        # Bloco de código cercado ```
        if stripped.startswith("```"):
            _descarregar_tabela()
            if em_codigo:
                texto_codigo = "\n".join(buffer_codigo)
                blocos.append(
                    Block(
                        id=_novo_id(),
                        kind=BlockKind.CODE_BLOCK,
                        spans=(InlineSpan(id="s1", kind=SpanKind.CODE_BLOCK, text=texto_codigo),),
                    )
                )
                buffer_codigo = []
                em_codigo = False
            else:
                em_codigo = True
            continue

        if em_codigo:
            buffer_codigo.append(linha_bruta)
            continue

        # Linha de tabela Markdown | a | b |
        if stripped.startswith("|") and stripped.endswith("|") and len(stripped) > 2:
            celulas = [c.strip() for c in stripped.strip("|").split("|")]
            # Ignora linha separadora |---|---|
            if all(re.fullmatch(r"[:\-]+", c) for c in celulas if c):
                continue
            buffer_tabela.append(celulas)
            continue
        else:
            _descarregar_tabela()

        if not stripped:
            continue

        # Se estivermos na seção de referências e surgir outro título sem indicativo pós-textual
        secao = secoes_por_linha.get(num_linha)
        if secao is not None:
            if em_referencias and linhas_referencia:
                _anexar_referencias_parseadas(blocos, "\n".join(linhas_referencia), _novo_id)
                linhas_referencia = []
                em_referencias = False

            if _REFERENCES_HEADING_RE.match(stripped) or secao.title.lower().startswith(
                ("referência", "referencia")
            ):
                em_referencias = True
                blocos.append(
                    Block(
                        id=_novo_id(),
                        kind=BlockKind.REFERENCES,
                        spans=(InlineSpan(id="s1", kind=SpanKind.TEXT, text="REFERÊNCIAS"),),
                        attributes={"level": 1, "unnumbered": True},
                    )
                )
                continue

            if secao.title.lower() in ("sumário", "sumario"):
                blocos.append(
                    Block(
                        id=_novo_id(),
                        kind=BlockKind.TABLE_OF_CONTENTS,
                        spans=(InlineSpan(id="s1", kind=SpanKind.TEXT, text="SUMÁRIO"),),
                    )
                )
                continue

            blocos.append(
                Block(
                    id=_novo_id(),
                    kind=BlockKind.HEADING,
                    spans=(InlineSpan(id="s1", kind=SpanKind.TEXT, text=secao.title),),
                    attributes={
                        "level": secao.level,
                        "number": secao.number,
                        "unnumbered": secao.kind == "unnumbered",
                    },
                )
            )
            continue

        if em_referencias:
            linhas_referencia.append(stripped)
            continue

        # Legenda ou fonte explícita
        if stripped.lower().startswith(("tabela ", "quadro ", "figura ", "gráfico ")):
            blocos.append(
                Block(
                    id=_novo_id(),
                    kind=BlockKind.CAPTION,
                    spans=(InlineSpan(id="s1", kind=SpanKind.TEXT, text=stripped),),
                )
            )
            continue

        if stripped.lower().startswith("fonte:"):
            blocos.append(
                Block(
                    id=_novo_id(),
                    kind=BlockKind.SOURCE_NOTE,
                    spans=(InlineSpan(id="s1", kind=SpanKind.TEXT, text=stripped),),
                )
            )
            continue

        # Citação longa (> no início ou bloco marcado)
        if stripped.startswith(">"):
            texto_citacao = stripped.lstrip(">").strip()
            blocos.append(
                Block(
                    id=_novo_id(),
                    kind=BlockKind.QUOTE_LONG,
                    spans=(InlineSpan(id="s1", kind=SpanKind.QUOTE, text=texto_citacao),),
                )
            )
            continue

        blocos.append(
            Block(
                id=_novo_id(),
                kind=BlockKind.PARAGRAPH,
                spans=(InlineSpan(id="s1", kind=SpanKind.TEXT, text=stripped),),
            )
        )

    _descarregar_tabela()
    if em_referencias and linhas_referencia:
        _anexar_referencias_parseadas(blocos, "\n".join(linhas_referencia), _novo_id)

    return tuple(blocos)


def _anexar_referencias_parseadas(
    blocos: list[Block],
    bloco_texto: str,
    novo_id_fn: Callable[[], str],
) -> None:
    referencias = parse_references(bloco_texto)
    if referencias:
        for ref in referencias:
            formatada = (
                format_reference(ref)
                if (ref.authors and ref.title)
                else _sanitize_text(bloco_texto)
            )
            blocos.append(
                Block(
                    id=novo_id_fn(),
                    kind=BlockKind.REFERENCE_ITEM,
                    spans=(InlineSpan(id="s1", kind=SpanKind.TEXT, text=formatada),),
                )
            )
    else:
        for linha in bloco_texto.splitlines():
            if linha.strip():
                blocos.append(
                    Block(
                        id=novo_id_fn(),
                        kind=BlockKind.REFERENCE_ITEM,
                        spans=(
                            InlineSpan(id="s1", kind=SpanKind.TEXT, text=_sanitize_text(linha)),
                        ),
                    )
                )


def _append_spans_to_paragraph(paragraph: Paragraph, block: Block) -> None:
    """Adiciona os spans inline ao parágrafo preservando ênfase, código e campos ``REF``."""
    if not block.spans:
        return
    for span in block.spans:
        if span.kind is SpanKind.CODE_BLOCK:
            paragraph.add_run(span.text)
            continue
        texto_limpo = _sanitize_text(span.text)
        if not texto_limpo:
            continue
        # Suporte a marcadores de referência cruzada [[REF:sec_1]]
        ultimo_idx = 0
        for match in _REF_PLACEHOLDER_RE.finditer(texto_limpo):
            antes = texto_limpo[ultimo_idx : match.start()]
            if antes:
                run = paragraph.add_run(antes)
                _estilizar_run_por_span(run, span)
            add_ref_field(paragraph, match.group(1))
            ultimo_idx = match.end()
        resto = texto_limpo[ultimo_idx:]
        if resto:
            run = paragraph.add_run(resto)
            _estilizar_run_por_span(run, span)


def _estilizar_run_por_span(run: Run, span: InlineSpan) -> None:
    if span.kind is SpanKind.STRONG:
        run.bold = True
    elif span.kind is SpanKind.EMPHASIS:
        run.italic = True
    elif span.kind is SpanKind.CODE_INLINE:
        run.font.name = "Courier New"


def build_docx(
    document: AcademicDocument,
    template: Template,
    *,
    include_pre_textual: bool = True,
) -> DocxBuildResult:
    """Constrói um arquivo DOCX nativo a partir de :class:`AcademicDocument` e :class:`Template`."""
    doc = docx.Document()
    _configure_styles(doc, template)
    _configure_page_and_headers(doc, template)
    enable_update_fields_on_open(doc)

    blocos = document.blocks if document.blocks else parse_text_to_blocks(document.current_text())
    existing_kinds = {b.kind for b in blocos}

    transformacoes: list[Transformation] = []
    avisos: list[str] = []

    if include_pre_textual:
        transformacoes.extend(
            _render_pre_textual_from_metadata(doc, document.metadata, template, existing_kinds)
        )

    # Calcula indicativos progressivos NBR 6024 para títulos numeráveis
    indices_headings: list[int] = []
    niveis_headings: list[int] = []
    for idx, bloco in enumerate(blocos):
        if bloco.kind is BlockKind.HEADING and not bloco.attributes.get("unnumbered", False):
            indices_headings.append(idx)
            niveis_headings.append(max(1, min(bloco.level, 4)))

    start_at = template.sections.start_at if template.sections is not None else 1
    numeros_gerados = progressive_numbers(niveis_headings, start_at=start_at)
    mapa_numeros = dict(zip(indices_headings, numeros_gerados, strict=False))

    bookmark_seq = 1
    for idx, bloco in enumerate(blocos):
        if bloco.kind is BlockKind.PAGE_BREAK:
            _add_page_break(doc)
            continue

        if bloco.kind in PAGE_BREAK_BLOCKS and idx > 0:
            _add_page_break(doc)

        if bloco.kind is BlockKind.CATALOG_RECORD:
            p_cat = doc.add_paragraph(style="Fonte")
            p_cat.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_cat.add_run(CATALOG_RECORD_RESERVATION_NOTE)
            continue

        if bloco.kind is BlockKind.TABLE_OF_CONTENTS:
            doc.add_paragraph("SUMÁRIO", style="Sem Indicativo")
            p_toc = doc.add_paragraph(style="Normal")
            p_toc.paragraph_format.first_line_indent = Cm(0.0)
            add_toc_field(p_toc, levels="1-3")
            continue

        if bloco.kind is BlockKind.REFERENCES:
            titulo_ref = _sanitize_text(bloco.plain_text) or "REFERÊNCIAS"
            doc.add_paragraph(titulo_ref.upper(), style="Sem Indicativo")
            for child in bloco.children:
                p_ref = doc.add_paragraph(style="Referencia")
                _append_spans_to_paragraph(p_ref, child)
            continue

        if bloco.kind is BlockKind.REFERENCE_ITEM:
            p_ref = doc.add_paragraph(style="Referencia")
            _append_spans_to_paragraph(p_ref, bloco)
            continue

        if bloco.kind is BlockKind.HEADING:
            sem_indicativo = bool(bloco.attributes.get("unnumbered", False))
            titulo_limpo = _sanitize_text(bloco.plain_text)
            # Remove prefixos Markdown ou numéricos duplicados caso o bloco tenha vindo cru
            m_md = _HEADING_MD_RE.match(titulo_limpo)
            if m_md:
                titulo_limpo = m_md.group(2).strip()
            m_num = _HEADING_NUM_RE.match(titulo_limpo)
            if m_num:
                titulo_limpo = m_num.group(2).strip()

            if sem_indicativo:
                p_head = doc.add_paragraph(titulo_limpo.upper(), style="Sem Indicativo")
            else:
                nivel = max(1, min(bloco.level, 4))
                estilo_cfg = style_for_level(template.styles, min(nivel, 3))
                numero = str(bloco.attributes.get("number") or mapa_numeros.get(idx, ""))
                texto_titulo = titulo_limpo.upper() if estilo_cfg.uppercase else titulo_limpo
                rotulo = f"{numero} {texto_titulo}".strip() if numero else texto_titulo
                p_head = doc.add_paragraph(rotulo, style=f"Heading {nivel}")
                bookmark_name = str(bloco.attributes.get("bookmark") or f"sec_{bookmark_seq}")
                add_bookmark(p_head, bookmark_name, bookmark_seq)
                bookmark_seq += 1
            continue

        if bloco.kind is BlockKind.QUOTE_LONG:
            p_quote = doc.add_paragraph(style="Citacao Longa")
            _append_spans_to_paragraph(p_quote, bloco)
            continue

        if bloco.kind is BlockKind.CAPTION:
            p_cap = doc.add_paragraph(style="Legenda")
            texto_cap = _sanitize_text(bloco.plain_text)
            p_cap.add_run(texto_cap)
            continue

        if bloco.kind is BlockKind.SOURCE_NOTE:
            p_src = doc.add_paragraph(style="Fonte")
            p_src.add_run(_sanitize_text(bloco.plain_text))
            continue

        if bloco.kind is BlockKind.CODE_BLOCK:
            p_code = doc.add_paragraph(style="Codigo")
            p_code.add_run(bloco.plain_text)
            continue

        if bloco.kind is BlockKind.TABLE and bloco.table is not None:
            _render_table_block(doc, bloco.table, bookmark_seq)
            bookmark_seq += 1
            continue

        if bloco.kind is BlockKind.FIGURE:
            p_fig_cap = doc.add_paragraph(style="Legenda")
            p_fig_cap.add_run("Figura ")
            add_seq_field(p_fig_cap, "Figura")
            caption_txt = _sanitize_text(str(bloco.attributes.get("caption") or bloco.plain_text))
            if caption_txt:
                p_fig_cap.add_run(f" — {caption_txt}")
            add_bookmark(p_fig_cap, f"fig_{bookmark_seq}", bookmark_seq)
            bookmark_seq += 1
            source_txt = _sanitize_text(str(bloco.attributes.get("source") or ""))
            if source_txt:
                p_fig_src = doc.add_paragraph(style="Fonte")
                p_fig_src.add_run(
                    source_txt
                    if source_txt.lower().startswith("fonte:")
                    else f"Fonte: {source_txt}"
                )
            continue

        # Parágrafo padrão ou nota
        p_norm = doc.add_paragraph(style="Normal")
        _append_spans_to_paragraph(p_norm, bloco)

    transformacoes.append(
        Transformation(
            stage=PipelineStage.EXPORT,
            rule_id="export.docx.styles_applied",
            description="Estilos nativos do Word aplicados ao documento.",
            count=len(blocos),
        )
    )

    buffer = io.BytesIO()
    doc.save(buffer)
    docx_bytes = buffer.getvalue()
    inspecao = inspect_docx(docx_bytes)

    if inspecao.has_toc_field:
        avisos.append(
            "O sumário é um campo dinâmico TOC real do Word; atualize os campos (F9) ao abrir no "
            "editor para exibir a paginação atualizada."
        )

    return DocxBuildResult(
        content=docx_bytes,
        transformations=tuple(transformacoes),
        warnings=tuple(avisos),
        inspection=inspecao,
    )


def _render_table_block(doc: DocumentObject, table_data: TableData, bookmark_id: int) -> None:
    """Renderiza tabela atômica com legenda numerada via campo ``SEQ`` e fonte."""
    p_cap = doc.add_paragraph(style="Legenda")
    p_cap.add_run("Tabela ")
    add_seq_field(p_cap, "Tabela")
    if table_data.caption:
        p_cap.add_run(f" — {_sanitize_text(table_data.caption)}")
    add_bookmark(p_cap, f"tab_{bookmark_id}", bookmark_id)

    if table_data.rows and table_data.column_count > 0:
        word_table = doc.add_table(rows=len(table_data.rows), cols=table_data.column_count)
        word_table.style = "Table Grid"
        for r_idx, row in enumerate(table_data.rows):
            for c_idx, cell_value in enumerate(row):
                if c_idx < table_data.column_count:
                    cell = word_table.cell(r_idx, c_idx)
                    cell.text = _sanitize_text(cell_value)
                    if r_idx == 0:
                        for p in cell.paragraphs:
                            for run in p.runs:
                                run.bold = True

    if table_data.source:
        p_src = doc.add_paragraph(style="Fonte")
        texto_fonte = _sanitize_text(table_data.source)
        p_src.add_run(
            texto_fonte if texto_fonte.lower().startswith("fonte:") else f"Fonte: {texto_fonte}"
        )


def inspect_docx(docx_bytes: bytes) -> DocxInspection:
    """Inspeciona ``styles.xml``, ``document.xml`` e ``settings.xml`` de um DOCX."""
    style_names: list[str] = []
    paragraph_styles_used: list[str] = []
    has_alignment_simulation = False
    catalog_record_reserved = True
    table_count = 0
    heading_count = 0
    has_update_fields = False
    page_width_cm = 0.0
    page_height_cm = 0.0
    margins_cm: dict[str, float] = {}

    style_id_to_name: dict[str, str] = {}

    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as archive:
        # 1. styles.xml
        if "word/styles.xml" in archive.namelist():
            styles_root = ET.fromstring(archive.read("word/styles.xml"))  # noqa: S314
            for st in styles_root.findall(f".//{{{_W_NS}}}style"):
                st_id = st.get(f"{{{_W_NS}}}styleId", "")
                name_el = st.find(f"{{{_W_NS}}}name")
                name_val = name_el.get(f"{{{_W_NS}}}val", "") if name_el is not None else st_id
                if name_val.lower().startswith("heading "):
                    name_val = "Heading " + name_val.split(" ", 1)[1]
                if name_val:
                    style_names.append(name_val)
                    style_id_to_name[st_id] = name_val

        # 2. settings.xml
        if "word/settings.xml" in archive.namelist():
            settings_root = ET.fromstring(archive.read("word/settings.xml"))  # noqa: S314
            upd = settings_root.find(f".//{{{_W_NS}}}updateFields")
            if upd is not None and upd.get(f"{{{_W_NS}}}val") in ("true", "1"):
                has_update_fields = True

        # 3. document.xml
        if "word/document.xml" in archive.namelist():
            doc_root = ET.fromstring(archive.read("word/document.xml"))  # noqa: S314
            table_count = len(doc_root.findall(f".//{{{_W_NS}}}tbl"))

            for para in doc_root.findall(f".//{{{_W_NS}}}p"):
                p_style_el = para.find(f"./{{{_W_NS}}}pPr/{{{_W_NS}}}pStyle")
                st_id = (
                    p_style_el.get(f"{{{_W_NS}}}val", "Normal")
                    if p_style_el is not None
                    else "Normal"
                )
                st_name = style_id_to_name.get(st_id, st_id)
                if st_name not in paragraph_styles_used:
                    paragraph_styles_used.append(st_name)
                if st_name.startswith("Heading"):
                    heading_count += 1

                # Verifica simulação de alinhamento com espaços/tabs fora de código
                if st_name != "Codigo":
                    texto_para = "".join(t.text or "" for t in para.findall(f".//{{{_W_NS}}}t"))
                    if "\t" in texto_para or "    " in texto_para:
                        has_alignment_simulation = True
                    if "ficha catalográfica" in texto_para.lower() and (
                        "isbn 000" in texto_para.lower() or "cdd 000" in texto_para.lower()
                    ):
                        catalog_record_reserved = False

            sect_pr = doc_root.find(f".//{{{_W_NS}}}sectPr")
            if sect_pr is not None:
                pg_sz = sect_pr.find(f"{{{_W_NS}}}pgSz")
                if pg_sz is not None:
                    w_twips = float(pg_sz.get(f"{{{_W_NS}}}w", "0"))
                    h_twips = float(pg_sz.get(f"{{{_W_NS}}}h", "0"))
                    page_width_cm = round(w_twips / _TWIPS_PER_CM, 2)
                    page_height_cm = round(h_twips / _TWIPS_PER_CM, 2)
                pg_mar = sect_pr.find(f"{{{_W_NS}}}pgMar")
                if pg_mar is not None:
                    for lado in ("top", "bottom", "left", "right"):
                        val_twips = float(pg_mar.get(f"{{{_W_NS}}}{lado}", "0"))
                        margins_cm[lado] = round(val_twips / _TWIPS_PER_CM, 2)

    fields = tuple(extract_field_instructions(docx_bytes))
    has_toc = any(f.upper().startswith("TOC") for f in fields)
    has_page = any(f.upper() == "PAGE" or f.upper().startswith("PAGE ") for f in fields)

    return DocxInspection(
        style_names=tuple(style_names),
        paragraph_styles_used=tuple(paragraph_styles_used),
        fields=fields,
        has_toc_field=has_toc,
        has_page_field=has_page,
        has_update_fields=has_update_fields,
        has_alignment_simulation=has_alignment_simulation,
        catalog_record_reserved=catalog_record_reserved,
        table_count=table_count,
        heading_count=heading_count,
        page_width_cm=page_width_cm,
        page_height_cm=page_height_cm,
        margins_cm=margins_cm,
    )
