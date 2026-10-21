"""Testes da identificação e consulta de DOI."""

from __future__ import annotations

from collections.abc import Mapping

import httpx

from app.services.references.doi import DOIResolver, identify_dois
from app.services.references.models import Author, Reference, ReferenceType


def test_identify_dois() -> None:
    texto = "DOI: 10.1111/abc.123 e outro 10.2222/xyz.456. Veja 10.1111/abc.123 de novo."
    assert identify_dois(texto) == ["10.1111/abc.123", "10.2222/xyz.456"]


def test_identify_dois_vazio() -> None:
    assert identify_dois("sem doi") == []


def _transporte(payload: Mapping[str, object]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload, request=request)

    return httpx.MockTransport(handler)


async def test_fetch_metadata() -> None:
    payload = {
        "message": {
            "title": ["Titulo correto"],
            "volume": "10",
            "issued": {"date-parts": [[2021]]},
        }
    }
    resolver = DOIResolver(transport=_transporte(payload))
    metadata = await resolver.fetch_metadata("10.1111/abc.123")
    assert metadata is not None
    assert metadata["title"] == ["Titulo correto"]


async def test_fetch_metadata_erro_devolve_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={}, request=request)

    resolver = DOIResolver(transport=httpx.MockTransport(handler))
    assert await resolver.fetch_metadata("10.1111/abc.123") is None


def test_propose_changes() -> None:
    ref = Reference(
        id="r1",
        type=ReferenceType.ARTICLE,
        authors=(Author(surname="Silva", given="R."),),
        title="Titulo errado",
        year="2020",
        doi="10.1111/abc.123",
    )
    metadata = {
        "title": ["Titulo correto"],
        "issued": {"date-parts": [[2021]]},
    }
    mudancas = DOIResolver().propose_changes(ref, metadata)
    campos = {m.field: m for m in mudancas}
    assert campos["title"].proposed == "Titulo correto"
    assert campos["year"].proposed == "2021"
