"""Testes unitários do construtor DOCX e inspetor estrutural (Onda 6)."""

from __future__ import annotations

from app.ir.blocks import Block, BlockKind, TableData
from app.ir.document import AcademicDocument, DocumentMetadata, DocumentNature
from app.ir.spans import InlineSpan, SpanKind
from app.services.academic.templates import TemplateRegistry
from app.services.document_export.docx_builder import (
    CATALOG_RECORD_RESERVATION_NOTE,
    build_docx,
    inspect_docx,
    parse_text_to_blocks,
)

SAMPLE_ACADEMIC_TEXT = """# Introdução

Este estudo analisa a concentração de 10⁻⁶ mol/L conforme (Silva, 2023, p. 42).
Consulte também a seção [[REF:sec_1]] para detalhes metodológicos.

## Materiais e Métodos

> A citação direta com mais de três linhas deve ter recuo de 4 cm da margem
> esquerda, letra menor que a do texto utilizado e sem aspas, conforme a
> ABNT NBR 10520:2023.

| Amostra | Valor |
|---|---|
| A1 | 12,4 |
| A2 | 15,8 |

Fonte: Elaborado pelo autor (2026).

```python
def calcular_media(valores: list[float]) -> float:
    return sum(valores) / len(valores)
```

# Conclusão

Os resultados confirmam a hipótese inicial.

REFERÊNCIAS

SILVA, João Carlos. Metodologia científica aplicada. São Paulo: Atlas, 2023.
"""


def test_build_docx_preserves_native_styles_and_toc_field(
    template_registry: TemplateRegistry,
) -> None:
    template = template_registry.get("abnt.tcc")
    meta = DocumentMetadata(
        institution="Universidade Federal de Mato Grosso do Sul",
        academic_unit="Faculdade de Computação",
        author="Maria Oliveira",
        title="Análise de Sistemas Acadêmicos",
        subtitle="Um Estudo Experimental",
        nature=DocumentNature.TCC,
        advisor="Prof. Dr. Carlos Souza",
        city="Campo Grande",
        year="2026",
    )
    doc = AcademicDocument(
        id="doc-tcc-1",
        original_text=SAMPLE_ACADEMIC_TEXT,
        metadata=meta,
    )

    result = build_docx(doc, template, include_pre_textual=True)
    inspecao = result.inspection

    # Estilos nativos criados em styles.xml e usados em document.xml
    assert "Normal" in inspecao.style_names
    assert "Heading 1" in inspecao.style_names
    assert "Heading 2" in inspecao.style_names
    assert "Citacao Longa" in inspecao.style_names
    assert "Legenda" in inspecao.style_names
    assert "Fonte" in inspecao.style_names
    assert "Referencia" in inspecao.style_names
    assert "Sem Indicativo" in inspecao.style_names

    assert "Heading 1" in inspecao.paragraph_styles_used
    assert "Heading 2" in inspecao.paragraph_styles_used
    assert "Citacao Longa" in inspecao.paragraph_styles_used
    assert "Referencia" in inspecao.paragraph_styles_used
    assert "Sem Indicativo" in inspecao.paragraph_styles_used

    # Campos reais do Word (TOC, PAGE, SEQ, REF) e w:updateFields
    assert inspecao.has_toc_field is True
    assert inspecao.has_page_field is True
    assert inspecao.has_update_fields is True
    assert any(f.startswith("SEQ Tabela") for f in inspecao.fields)
    assert any(f.startswith("REF sec_1") for f in inspecao.fields)

    # Nenhuma simulação visual com espaços/tabs repetidos
    assert inspecao.has_alignment_simulation is False

    # Ficha catalográfica reservada, nunca fictícia
    assert inspecao.catalog_record_reserved is True
    assert inspecao.table_count == 1
    assert inspecao.heading_count >= 2

    # Tamanho A4 e margens da NBR 14724:2024 (3/2/3/2 cm)
    assert abs(inspecao.page_width_cm - 21.0) <= 0.05
    assert abs(inspecao.page_height_cm - 29.7) <= 0.05
    assert inspecao.margins_cm["top"] == 3.0
    assert inspecao.margins_cm["left"] == 3.0
    assert inspecao.margins_cm["bottom"] == 2.0
    assert inspecao.margins_cm["right"] == 2.0


def test_build_docx_strips_simulated_alignment_spaces_and_tabs(
    template_registry: TemplateRegistry,
) -> None:
    template = template_registry.get("abnt.general")
    texto_com_espacos = (
        "1 Introdução\n\n"
        "Parágrafo     com     muitos    espaços\t\te\ttabulações     simulando alinhamento.\n"
    )
    doc = AcademicDocument(id="doc-clean", original_text=texto_com_espacos)
    result = build_docx(doc, template, include_pre_textual=False)

    assert result.inspection.has_alignment_simulation is False
    # Documento original permanece intocado
    assert "\t\t" in doc.original_text


def test_build_docx_with_explicit_ir_blocks_figures_and_tables(
    template_registry: TemplateRegistry,
) -> None:
    template = template_registry.resolve("abnt.tcc", "inst.ufms.geral").template
    blocks = (
        Block(
            id="b1",
            kind=BlockKind.CATALOG_RECORD,
            spans=(InlineSpan(id="s1", kind=SpanKind.TEXT, text=CATALOG_RECORD_RESERVATION_NOTE),),
        ),
        Block(
            id="b2",
            kind=BlockKind.TABLE_OF_CONTENTS,
        ),
        Block(
            id="b3",
            kind=BlockKind.HEADING,
            spans=(InlineSpan(id="s2", kind=SpanKind.TEXT, text="Resultados"),),
            attributes={"level": 1},
        ),
        Block(
            id="b4",
            kind=BlockKind.PARAGRAPH,
            spans=(
                InlineSpan(id="s3", kind=SpanKind.STRONG, text="Importante: "),
                InlineSpan(id="s4", kind=SpanKind.EMPHASIS, text="ênfase "),
                InlineSpan(id="s5", kind=SpanKind.CODE_INLINE, text="x = 1"),
            ),
        ),
        Block(
            id="b5",
            kind=BlockKind.FIGURE,
            spans=(InlineSpan(id="s6", kind=SpanKind.TEXT, text="Arquitetura do sistema"),),
            attributes={"caption": "Arquitetura em camadas", "source": "O autor (2026)"},
        ),
        Block(
            id="b6",
            kind=BlockKind.TABLE,
            table=TableData(
                rows=(("Métrica", "Valor"), ("Precisão", "98%")),
                column_count=2,
                caption="Desempenho",
                source="Dados da pesquisa",
            ),
        ),
        Block(
            id="b7",
            kind=BlockKind.PAGE_BREAK,
        ),
        Block(
            id="b8",
            kind=BlockKind.REFERENCES,
            spans=(InlineSpan(id="s7", kind=SpanKind.TEXT, text="REFERÊNCIAS"),),
            children=(
                Block(
                    id="b9",
                    kind=BlockKind.REFERENCE_ITEM,
                    spans=(
                        InlineSpan(
                            id="s8",
                            kind=SpanKind.TEXT,
                            text=(
                                "SOUZA, M. B. Sistemas distribuídos. "
                                "Rio de Janeiro: Elsevier, 2022."
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    doc = AcademicDocument(id="doc-blocks", original_text="Texto original", blocks=blocks)
    res = build_docx(doc, template, include_pre_textual=False)
    inspecao = inspect_docx(res.content)

    assert inspecao.has_toc_field is True
    assert inspecao.table_count == 1
    assert any(f.startswith("SEQ Figura") for f in inspecao.fields)
    assert any(f.startswith("SEQ Tabela") for f in inspecao.fields)
    assert inspecao.has_alignment_simulation is False


def test_parse_text_to_blocks_covers_unnumbered_and_captions() -> None:
    texto = (
        "RESUMO\n\n"
        "Texto do resumo.\n\n"
        "SUMÁRIO\n\n"
        "1.1 Subseção\n\n"
        "Tabela 1 — Resumo dos dados\n\n"
        "Fonte: O autor.\n"
    )
    blocos = parse_text_to_blocks(texto)
    kinds = [b.kind for b in blocos]
    assert BlockKind.HEADING in kinds
    assert BlockKind.TABLE_OF_CONTENTS in kinds
    assert BlockKind.CAPTION in kinds
    assert BlockKind.SOURCE_NOTE in kinds
