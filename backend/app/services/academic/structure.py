"""Detecção determinística da estrutura do documento.

Identifica títulos de seção no texto plano — por marcação Markdown, por
numeração progressiva ABNT (``1``, ``1.1``, ``1.1.1``) e por títulos sem
indicativo em caixa alta (referências, sumário, apêndice...). A LLM **não**
participa da estruturação (ver `ADR-0005`).
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

#: Títulos sem indicativo numérico, comuns em pré e pós-textuais.
_TITULOS_SEM_INDICATIVO = frozenset(
    {
        "resumo",
        "abstract",
        "sumário",
        "sumario",
        "referências",
        "referencias",
        "referências bibliográficas",
        "glossário",
        "glossario",
        "apêndice",
        "apendice",
        "apêndices",
        "apendices",
        "anexo",
        "anexos",
        "índice",
        "indice",
        "índice remissivo",
        "dedicatória",
        "dedicatoria",
        "agradecimentos",
        "epígrafe",
        "epigrafe",
        "lista de ilustrações",
        "lista de tabelas",
        "lista de abreviaturas",
        "lista de símbolos",
        "errata",
    }
)

_HEADING_MD_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_HEADING_NUM_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+(.+?)\s*$")
_TITLE_PLAIN_RE = re.compile(r"^([A-ZÀ-Ü][^a-zà-ü]{3,80})$")


class Section(BaseModel):
    """Seção detectada no texto."""

    model_config = ConfigDict(frozen=True)

    level: int
    """Nível hierárquico (1 = primário)."""

    title: str
    """Título sem o indicativo numérico."""

    number: str = ""
    """Indicativo numérico (``1``, ``1.1``) ou vazio para títulos sem indicativo."""

    line: int
    """Número da linha (base 0)."""

    kind: str = "heading"
    """``heading`` | ``unnumbered``."""


def detect_structure(text: str) -> list[Section]:
    """Detecta as seções do texto, na ordem em que aparecem."""
    secoes: list[Section] = []
    for numero_linha, linha in enumerate(text.splitlines()):
        stripped = linha.strip()
        if not stripped:
            continue

        match_md = _HEADING_MD_RE.match(stripped)
        if match_md:
            nivel = len(match_md.group(1))
            secoes.append(
                Section(
                    level=nivel,
                    title=match_md.group(2).strip(),
                    number="",
                    line=numero_linha,
                    kind="heading",
                )
            )
            continue

        match_num = _HEADING_NUM_RE.match(stripped)
        if match_num:
            numero = match_num.group(1)
            nivel = numero.count(".") + 1
            secoes.append(
                Section(
                    level=nivel,
                    title=match_num.group(2).strip(),
                    number=numero,
                    line=numero_linha,
                    kind="heading",
                )
            )
            continue

        if _is_titulo_sem_indicativo(stripped):
            secoes.append(
                Section(
                    level=1,
                    title=stripped,
                    number="",
                    line=numero_linha,
                    kind="unnumbered",
                )
            )

    return secoes


def _is_titulo_sem_indicativo(linha: str) -> bool:
    """Indica se a linha é um título sem indicativo (caixa alta e conhecido)."""
    if not _TITLE_PLAIN_RE.match(linha):
        return False
    normalizado = linha.lower()
    for titulo in _TITULOS_SEM_INDICATIVO:
        if normalizado == titulo or normalizado.startswith(titulo + " "):
            return True
    return False
