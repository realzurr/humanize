"""Identificação de DOI e consulta opt-in de metadados.

A consulta a serviços externos (Crossref/DataCite) é **opt-in**: só ocorre
quando o usuário pede e quando ``Settings.enable_doi_lookup`` é verdadeiro.
Os metadados recebidos geram **propostas de alteração** — nunca são aplicados
automaticamente (o usuário aprova ou rejeita cada uma).
"""

from __future__ import annotations

import re
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from app.services.references.models import Reference

#: Identificador DOI (permite ``.``, ``-``, ``_``, ``;``, ``/``, ``:``).
DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")

#: Campos comparados na proposta de alteração.
_COMPARED_FIELDS = ("title", "year", "container", "volume", "issue", "pages", "publisher")


class ProposedChange(BaseModel):
    """Alteração de metadado proposta a partir de um DOI."""

    model_config = ConfigDict(frozen=True)

    field: str
    current: str
    proposed: str
    source: str = "crossref"
    confidence: str = "high"


def identify_dois(text: str) -> list[str]:
    """Devolve os DOIs encontrados no texto, sem duplicar e em ordem."""
    vistos: set[str] = set()
    resultado: list[str] = []
    for match in DOI_RE.finditer(text):
        doi = match.group(0).rstrip(".,;")
        if doi not in vistos:
            vistos.add(doi)
            resultado.append(doi)
    return resultado


class DOIResolver:
    """Consulta metadados de DOI (Crossref), com transporte injetável."""

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout_seconds: float = 15.0,
        user_agent: str = "HumanizaAcademico/0.1",
    ) -> None:
        self._transport = transport
        self._timeout = timeout_seconds
        self._user_agent = user_agent

    async def fetch_metadata(self, doi: str) -> dict[str, Any] | None:
        """Consulta o Crossref por metadados do DOI (sem rede quando mockado)."""
        url = f"https://api.crossref.org/works/{doi}"
        headers = {"User-Agent": self._user_agent}
        try:
            async with httpx.AsyncClient(
                transport=self._transport, timeout=self._timeout
            ) as client:
                resposta = await client.get(url, headers=headers)
        except httpx.HTTPError:
            return None
        if resposta.status_code != 200:
            return None
        dados = resposta.json()
        mensagem = dados.get("message")
        return mensagem if isinstance(mensagem, dict) else None

    def propose_changes(
        self,
        reference: Reference,
        metadata: dict[str, Any],
    ) -> list[ProposedChange]:
        """Compara a referência com os metadados do Crossref e propõe mudanças."""
        proposta = _crossref_para_referencia(metadata)
        mudancas: list[ProposedChange] = []
        for campo in _COMPARED_FIELDS:
            atual = getattr(reference, campo, "")
            sugerido = proposta.get(campo, "")
            if atual and sugerido and _normalizar(atual) != _normalizar(sugerido):
                mudancas.append(ProposedChange(field=campo, current=atual, proposed=sugerido))
        return mudancas


def _crossref_para_referencia(metadata: dict[str, Any]) -> dict[str, str]:
    titulos = metadata.get("title") or []
    titulo = titulos[0] if isinstance(titulos, list) and titulos else ""

    containers = metadata.get("container-title") or []
    container = containers[0] if isinstance(containers, list) and containers else ""

    ano = ""
    issued = metadata.get("issued") or {}
    if isinstance(issued, dict):
        partes = issued.get("date-parts") or []
        if partes and isinstance(partes[0], list) and partes[0]:
            ano = str(partes[0][0])

    paginas = str(metadata.get("page") or "")

    return {
        "title": str(titulo),
        "year": ano,
        "container": str(container),
        "volume": str(metadata.get("volume") or ""),
        "issue": str(metadata.get("issue") or ""),
        "pages": paginas,
        "publisher": str(metadata.get("publisher") or ""),
    }


def _normalizar(valor: str) -> str:
    return re.sub(r"\s+", " ", valor).strip().lower()
