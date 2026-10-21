"""Extração de citações do texto.

Identifica citações autor-data (``(SILVA, 2020)``, ``Silva (2020)``, ``Silva;
Souza, 2021``) e numéricas (``[12]``, ``[1, 2]``, ``[3-5]``), classificando as
diretas (entre aspas, com indicação de página) e as longas (mais de três
linhas, que na Onda 6 recebem recuo de 4 cm).
"""

from __future__ import annotations

import re

from app.ir.spans import SourceRange
from app.services.references.models import Citation, CitationKind

#: Citação numérica: [12], [1, 2], [3-5].
_NUMERIC_RE = re.compile(r"\[(\d+(?:\s*[-–,;]\s*\d+)*)\]")

#: Citação autor-data entre parênteses (``(SILVA, 2020)``,
#: ``(SOUZA; PEREIRA, 2018)``, ``(SILVA, 2020, p. 45)``).
_AUTHOR_DATE_RE = re.compile(
    r"\(((?:[A-ZÀ-Ü][A-ZÀ-Ü'’\- ]+)(?:\s*;\s*[A-ZÀ-Ü][A-ZÀ-Ü'’\- ]+)*"
    r"\s*(?:,|;)?\s*(?:19|20)\d{2}[a-z]?"
    r"[^)]*)\)"
)

#: Citação autor-data fora de parênteses (``Silva (2020)``).
#: Captura apenas o sobrenome (uma palavra), para não engolir marcadores
#: discursivos como "Segundo Silva (2020)".
_NAKED_AUTHOR_YEAR_RE = re.compile(r"([A-ZÀ-Ü][a-zà-ü'’\-]+)\s+\(((?:19|20)\d{2}[a-z]?)\)")

_YEAR_RE = re.compile(r"((?:19|20)\d{2}[a-z]?)")

#: Marca de citação literal (aspas).
_QUOTE_MARK = re.compile(r"[“”\"']")


def parse_citations(text: str) -> list[Citation]:
    """Extrai as citações do texto, na ordem em que aparecem."""
    citacoes: list[Citation] = []
    contador = 0

    for match in _NUMERIC_RE.finditer(text):
        numeros = _expand_numbers(match.group(1))
        contador += 1
        citacoes.append(
            Citation(
                id=f"cit{contador:04d}",
                kind=CitationKind.INDIRECT,
                numeric=True,
                numbers=tuple(numeros),
                source_range=SourceRange(start=match.start(), end=match.end()),
            )
        )

    for match in _AUTHOR_DATE_RE.finditer(text):
        contador += 1
        autores, ano = _parse_author_date(match.group(1))
        citacoes.append(
            Citation(
                id=f"cit{contador:04d}",
                kind=_classificar(match, text),
                numeric=False,
                authors=tuple(autores),
                year=ano,
                source_range=SourceRange(start=match.start(), end=match.end()),
            )
        )

    for match in _NAKED_AUTHOR_YEAR_RE.finditer(text):
        contador += 1
        citacoes.append(
            Citation(
                id=f"cit{contador:04d}",
                kind=CitationKind.INDIRECT,
                numeric=False,
                authors=(match.group(1).upper(),),
                year=match.group(2),
                source_range=SourceRange(start=match.start(), end=match.end()),
            )
        )

    return _ordenar(citacoes)


def _expand_numbers(grupo: str) -> list[int]:
    """Expande ``1-3`` em ``[1, 2, 3]`` e ``1, 2`` em ``[1, 2]``."""
    numeros: list[int] = []
    for parte in re.split(r"[;,]", grupo):
        parte = parte.strip()
        if not parte:
            continue
        intervalo = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", parte)
        if intervalo:
            inicio = int(intervalo.group(1))
            fim = int(intervalo.group(2))
            numeros.extend(range(inicio, fim + 1))
        else:
            numeros.append(int(parte))
    return numeros


def _parse_author_date(conteudo: str) -> tuple[list[str], str]:
    """Extrai sobrenomes e ano de um conteúdo autor-data."""
    autores: list[str] = []
    ano = ""
    # Remove a indicação de página, quando presente (``, p. 45``).
    conteudo = re.sub(r",?\s*p\.?\s*\d+.*$", "", conteudo).strip()
    for parte in conteudo.split(";"):
        parte = parte.strip()
        m = _YEAR_RE.search(parte)
        if m:
            ano = m.group(1)
        nome = _YEAR_RE.sub("", parte).strip(" ,")
        if nome:
            autores.append(nome.upper())
    return autores, ano


def _classificar(match: re.Match[str], text: str) -> CitationKind:
    """Classifica a citação em direta/indireta pela presença de aspas."""
    janela = text[max(0, match.start() - 3) : match.end() + 3]
    if _QUOTE_MARK.search(janela):
        return CitationKind.DIRECT
    return CitationKind.INDIRECT


def _ordenar(citacoes: list[Citation]) -> list[Citation]:
    return sorted(
        citacoes,
        key=lambda c: c.source_range.start if c.source_range is not None else 0,
    )
