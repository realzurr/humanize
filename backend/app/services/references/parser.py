"""Extração de entradas de referência a partir de texto.

O parser é heurístico: identifica a lista de referências (após o cabeçalho
"Referências"), separa as entradas (cada uma iniciada por ``SOBRENOME,``) e
extrai autores, título, periódico/editora, ano, DOI e URL. Metadados ausentes
**não** são inventados — os campos ficam vazios e são sinalizados pelo
validador.
"""

from __future__ import annotations

import re

from app.ir.spans import SourceRange
from app.services.references.models import Author, Reference, ReferenceType

#: Cabeçalho de lista de referências.
_REFERENCES_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:refer[eê]ncias|refer[eê]ncias bibliogr[aá]ficas|bibliografia)\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

#: Início de uma entrada: sobrenome em caixa alta seguido de vírgula.
_ENTRY_START_RE = re.compile(r"^[A-ZÀ-Ü][A-ZÀ-Ü'’\- ]+,")

#: Fronteira entre blocos (autor/título/periódico): ``. `` seguido de
#: maiúscula + minúscula. Iniciais ``R. A.`` e DOIs não casam.
_BOUNDARY_RE = re.compile(r"\.\s+(?=[A-ZÀ-Ü][a-zà-ü])")

_DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
_URL_RE = re.compile(r"\bhttps?://[^\s<>\"']+")
_YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")


def find_references_block(text: str) -> str:
    """Devolve o bloco de referências (após o cabeçalho) ou o texto inteiro."""
    match = _REFERENCES_HEADING_RE.search(text)
    if match is None:
        return text
    return text[match.end() :].strip()


def parse_references(text: str) -> list[Reference]:
    """Extrai as entradas de referência do texto, com a localização original."""
    heading_match = _REFERENCES_HEADING_RE.search(text)
    bloco_inicio = heading_match.end() if heading_match else 0
    bloco = text[bloco_inicio:]

    referencias: list[Reference] = []
    for indice, (entrada, offset) in enumerate(_split_entries(bloco), start=1):
        referencia = parse_entry(entrada)
        if not (referencia.title or referencia.authors or referencia.doi):
            continue
        inicio = bloco_inicio + offset
        source = SourceRange(start=inicio, end=inicio + len(entrada))
        referencias.append(
            referencia.model_copy(update={"id": f"ref{indice:04d}", "source_range": source})
        )
    return referencias


def parse_entry(text: str) -> Reference:
    """Extrai os campos de uma entrada de referência (melhor esforço)."""
    limpo = " ".join(text.split()).strip()
    segmentos = [s.strip() for s in _BOUNDARY_RE.split(limpo) if s.strip()]

    autores = _parse_author_segment(segmentos[0]) if segmentos else []
    titulo = segmentos[1] if len(segmentos) > 1 else ""

    doi_match = _DOI_RE.search(limpo)
    doi = _limpar_doi(doi_match.group(0)) if doi_match else ""
    url_match = _URL_RE.search(limpo)
    url = url_match.group(0).rstrip(".,;") if url_match else ""

    anos = _YEAR_RE.findall(limpo)
    ano = anos[-1] if anos else ""

    tipo = _inferir_tipo(limpo, doi, url)
    local, editora = _extract_local_editora(tipo, limpo, segmentos)
    return Reference(
        id="",
        type=tipo,
        authors=tuple(autores),
        title=titulo,
        year=ano,
        container=_extract_container(segmentos),
        volume=_extract_field(limpo, r"\bv\.?\s*([\d-]+)"),
        issue=_extract_field(limpo, r"\bn\.?\s*([\d-]+)"),
        pages=_extract_field(limpo, r"\bp\.?\s*([\d\-–]+)"),
        publisher=editora,
        place=local,
        doi=doi,
        url=url,
        accessed_at=_extract_access(limpo),
    )


def _split_entries(bloco: str) -> list[tuple[str, int]]:
    """Separa o bloco de referências em entradas, com o offset de cada uma."""
    entradas: list[tuple[str, int]] = []
    partes: list[str] = []
    inicio: int | None = None
    offset = 0

    for linha in bloco.splitlines(keepends=True):
        conteudo = linha.strip()
        if _ENTRY_START_RE.match(conteudo) and partes:
            entradas.append((" ".join(partes).strip(), inicio or 0))
            partes = [conteudo]
            inicio = offset + (len(linha) - len(linha.lstrip()))
        else:
            if not partes:
                inicio = offset + (len(linha) - len(linha.lstrip()))
            partes.append(conteudo)
        offset += len(linha)

    if partes:
        entradas.append((" ".join(partes).strip(), inicio or 0))

    if not entradas and bloco.strip():
        entradas = [(bloco.strip(), 0)]

    return [(texto, inicio) for texto, inicio in entradas if texto]


def _parse_author_segment(segmento: str) -> list[Author]:
    """Converte ``SOUZA, M. B.; PEREIRA, D. F`` em autores."""
    autores: list[Author] = []
    for parte in segmento.split(";"):
        parte = parte.strip().rstrip(".")
        if not parte or "," not in parte:
            continue
        sobrenome, _, nomes = parte.partition(",")
        autores.append(Author(surname=sobrenome.strip(), given=nomes.strip()))
    return autores


def _extract_container(segmentos: list[str]) -> str:
    """Devolve o nome do periódico/veículo (3º segmento, antes do local)."""
    if len(segmentos) <= 2:
        return ""
    dados = segmentos[2]
    antes_dos_dados = re.split(r",\s*(?:v\.|n\.|p\.|\d{4})", dados, maxsplit=1)[0]
    return antes_dos_dados.split(",")[0].strip()


def _inferir_tipo(texto: str, doi: str, url: str) -> ReferenceType:
    minusculo = texto.lower()
    if "dissertação" in minusculo or "dissertacao" in minusculo:
        return ReferenceType.DISSERTATION
    if " tese" in minusculo or minusculo.startswith("tese"):
        return ReferenceType.THESIS
    if doi or (re.search(r"\bv\.?\s*[\d-]+", texto) and re.search(r"\bp\.?\s*[\d-]+", texto)):
        return ReferenceType.ARTICLE
    if url or "disponível em" in minusculo or "disponivel em" in minusculo:
        return ReferenceType.WEB
    return ReferenceType.BOOK


def _limpar_doi(doi: str) -> str:
    return re.sub(r"^doi:?", "", doi, flags=re.IGNORECASE).rstrip(".,;").strip()


def _extract_field(resto: str, pattern: str) -> str:
    m = re.search(pattern, resto, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _extract_local_editora(
    tipo: ReferenceType,
    texto: str,
    segmentos: list[str],
) -> tuple[str, str]:
    """Extrai local e editora conforme o tipo de referência.

    Livros e páginas web usam o padrão ``Local: Editora``; artigos têm o
    local logo após o nome do periódico (``Revista, São Paulo, v. 10``).
    """
    if tipo in (ReferenceType.BOOK, ReferenceType.WEB):
        for segmento in segmentos[2:]:
            if ":" not in segmento:
                continue
            if re.match(r"(disponível|disponivel|acesso|doi)", segmento, re.IGNORECASE):
                continue
            m = re.match(r"([^:]+):\s*([^,]+)", segmento)
            if m:
                return m.group(1).strip(), m.group(2).strip()
        return "", ""
    if tipo is ReferenceType.ARTICLE and len(segmentos) > 2:
        m = re.match(r"[^,]+,\s*([^,]+)", segmentos[2])
        if m:
            return m.group(1).strip(), ""
    return "", ""


def _extract_access(resto: str) -> str:
    m = re.search(r"(?:acesso em|acessado em)[:.]?\s*([\d\s\w./-]+)", resto, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def reference_from_source(text: str, source_range: SourceRange | None) -> Reference:
    """Extrai uma referência e anexa a localização no texto original."""
    referencia = parse_entry(text)
    return referencia.model_copy(update={"source_range": source_range})
