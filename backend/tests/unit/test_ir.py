"""Testes do documento intermediário (Onda 0 — modelos e invariantes)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.ir.blocks import Block, BlockKind
from app.ir.document import (
    AcademicDocument,
    DocumentMetadata,
    DocumentNature,
    DocumentRevision,
    PipelineStage,
    Transformation,
)
from app.ir.protection import (
    ProtectedEntity,
    ProtectedKind,
    ProtectionCatalog,
    ProtectionLevel,
    fingerprint,
    normalize_fingerprint,
)
from app.ir.spans import InlineSpan, SourceRange, SpanBuilder, SpanKind


class TestSourceRange:
    def test_slice_usa_offsets_em_code_points(self) -> None:
        text = "ação"
        rng = SourceRange(start=0, end=4)
        assert rng.slice(text) == text
        assert len(rng) == 4

    def test_end_menor_que_start_e_rejeitado(self) -> None:
        with pytest.raises(ValueError):
            SourceRange(start=5, end=2)

    def test_overlaps(self) -> None:
        a = SourceRange(start=0, end=10)
        b = SourceRange(start=5, end=15)
        c = SourceRange(start=10, end=20)
        assert a.overlaps(b)
        assert not a.overlaps(c)


class TestSpanBuilder:
    def test_reconstroi_o_texto_original(self) -> None:
        builder = SpanBuilder()
        builder.add("Texto ", kind=SpanKind.TEXT)
        builder.add("original", kind=SpanKind.EMPHASIS)
        assert builder.plain_text() == "Texto original"

    def test_spans_imutaveis(self) -> None:
        span = InlineSpan(id="s1", text="x")
        with pytest.raises(ValidationError):
            span.text = "y"  # type: ignore[misc]


class TestFingerprint:
    def test_normaliza_separador_de_milhar(self) -> None:
        assert normalize_fingerprint("1.000") == normalize_fingerprint("1000")

    def test_normaliza_sinal_menos_matematico(self) -> None:
        assert normalize_fingerprint("−5") == normalize_fingerprint("-5")

    def test_fingerprint_estavel(self) -> None:
        assert fingerprint("45,5%") == fingerprint("45.5%")
        assert fingerprint("45%") != fingerprint("45,5%")


class TestProtectionCatalog:
    def _entity(
        self, entity_id: str, kind: ProtectedKind, text: str, start: int
    ) -> ProtectedEntity:
        return ProtectedEntity(
            id=entity_id,
            kind=kind,
            text=text,
            source_range=SourceRange(start=start, end=start + len(text)),
            level=ProtectionLevel.CRITICAL,
            fingerprint=fingerprint(text),
            rule_id="test.rule",
        )

    def test_missing_fingerprints_detecta_perda(self) -> None:
        original = ProtectionCatalog(
            entities=(
                self._entity("P1", ProtectedKind.NUMBER, "45%", 0),
                self._entity("P2", ProtectedKind.NUMBER, "12 kg", 10),
            )
        )
        revised = ProtectionCatalog(entities=(self._entity("P1", ProtectedKind.NUMBER, "45%", 0),))
        assert original.missing_fingerprints(revised) == [fingerprint("12 kg")]

    def test_missing_fingerprints_ignora_valor_inalterado(self) -> None:
        original = ProtectionCatalog(entities=(self._entity("P1", ProtectedKind.NUMBER, "45%", 0),))
        revised = ProtectionCatalog(entities=(self._entity("P1", ProtectedKind.NUMBER, "45%", 0),))
        assert original.missing_fingerprints(revised) == []

    def test_in_range_encontra_sobrepostos(self) -> None:
        catalog = ProtectionCatalog(entities=(self._entity("P1", ProtectedKind.NUMBER, "45%", 5),))
        assert len(catalog.in_range(SourceRange(start=0, end=10))) == 1
        assert len(catalog.in_range(SourceRange(start=20, end=30))) == 0


class TestAcademicDocument:
    def test_original_text_e_imutavel(self) -> None:
        doc = AcademicDocument(id="d1", original_text="original")
        revision = DocumentRevision(id="r1", stage=PipelineStage.NORMALIZE, text="revisado")
        updated = doc.with_revision(revision)
        assert updated.original_text == "original"
        assert doc.revisions == ()
        assert updated.current_text() == "revisado"

    def test_current_text_sem_revisao_retorna_original(self) -> None:
        doc = AcademicDocument(id="d1", original_text="original")
        assert doc.current_text() == "original"

    def test_history_ordenado_por_criacao(self) -> None:
        doc = AcademicDocument(id="d1", original_text="x")
        r1 = DocumentRevision(id="r1", stage=PipelineStage.NORMALIZE, text="a")
        r2 = DocumentRevision(id="r2", stage=PipelineStage.HUMANIZE, text="b")
        doc = doc.with_revision(r1).with_revision(r2)
        assert [r.id for r in doc.history()] == ["r1", "r2"]


class TestDocumentMetadata:
    def test_missing_required(self) -> None:
        metadata = DocumentMetadata(institution="UFMS", title="")
        assert metadata.missing_required(("institution", "title", "author")) == [
            "title",
            "author",
        ]

    def test_nature_e_enum(self) -> None:
        metadata = DocumentMetadata(nature=DocumentNature.TESE)
        assert metadata.nature is DocumentNature.TESE


class TestBlock:
    def test_plain_text_concatena_spans(self) -> None:
        block = Block(
            id="b1",
            kind=BlockKind.PARAGRAPH,
            spans=(
                InlineSpan(id="s1", text="Olá"),
                InlineSpan(id="s2", text=" mundo"),
            ),
        )
        assert block.plain_text == "Olá mundo"

    def test_titulos_iniciam_em_nova_pagina(self) -> None:
        assert Block(id="b", kind=BlockKind.REFERENCES).starts_new_page
        assert not Block(id="b", kind=BlockKind.PARAGRAPH).starts_new_page


class TestTransformation:
    def test_registro_de_transformacao(self) -> None:
        t = Transformation(
            stage=PipelineStage.NORMALIZE,
            rule_id="norm.invisible.zwsp",
            count=3,
            severity="warning",
        )
        assert t.rule_id == "norm.invisible.zwsp"
        assert t.count == 3
