"""Segmentação do texto em trechos protegidos e livres.

Antes de qualquer regra de normalização, o texto é varrido para identificar
o conteúdo que **não pode** ser alterado automaticamente: números, unidades,
fórmulas, citações, referências, DOIs, URLs, código, tabelas e trechos de
citação literal.

O extrator devolve duas coisas:

1. um conjunto de **intervalos protegidos** (usado pelo motor para segmentar
   o texto antes de aplicar cada regra);
2. um :class:`~app.ir.protection.ProtectionCatalog` com as entidades
   detectadas (usado pela interface, pelo relatório e pela verificação de
   perda de dados protegidos).

A proteção é **conservadora por padrão**: quando há dúvida entre "proteger" e
"não proteger", protege-se. O custo de proteger demais é que algumas regras
não incidem sobre aquele trecho; o custo de proteger de menos é perda de
informação científica, que é proibido.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass

from app.ir.protection import (
    ProtectedEntity,
    ProtectedKind,
    ProtectionCatalog,
    default_level,
    fingerprint,
)
from app.ir.spans import SourceRange

#: Prefixo dos ``rule_id`` gerados pelo extrator.
RULE_ID_PREFIX = "protect"


@dataclass(frozen=True, slots=True)
class ProtectedSpan:
    """Intervalo do texto ocupado por conteúdo protegido."""

    start: int
    """Offset inicial (code points)."""

    end: int
    """Offset final, exclusivo."""

    kind: ProtectedKind
    """Categoria do conteúdo protegido."""

    @property
    def length(self) -> int:
        return self.end - self.start

    def overlaps(self, other: ProtectedSpan) -> bool:
        return self.start < other.end and other.start < self.end


#: Prioridade de resolução de sobreposições. Menor valor vence.
_PRIORIDADE: dict[ProtectedKind, int] = {
    ProtectedKind.CODE: 0,
    ProtectedKind.TABLE: 1,
    ProtectedKind.URL: 2,
    ProtectedKind.DOI: 3,
    ProtectedKind.QUOTE_LITERAL: 4,
    ProtectedKind.CITATION: 5,
    ProtectedKind.REFERENCE: 6,
    ProtectedKind.FORMULA: 7,
    ProtectedKind.STATISTIC: 8,
    ProtectedKind.NUMBER: 9,
    ProtectedKind.UNIT: 10,
    ProtectedKind.DATE: 11,
    ProtectedKind.TABLE_ID: 12,
    ProtectedKind.FIGURE_ID: 13,
}


# --------------------------------------------------------------------------
# Detectores
# --------------------------------------------------------------------------

_FENCED_CODE_RE = re.compile(r"```[\s\S]*?```|~~~[\s\S]*?~~~")
_INLINE_CODE_RE = re.compile(r"``[^`\n]+``|`[^`\n]+`")
_DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b")
_URL_RE = re.compile(
    r"\b(?:https?|ftp)://[^\s<>\"']*[^\s<>\"'.,;:!?)\]]|\bwww\.[^\s<>\"']*[^\s<>\"'.,;:!?)\]]"
)
_NUMBER_RE = re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)*(?:\s*[%‰])?(?![\w])")
_UNIT_RE = re.compile(
    r"(?<![\w])(?:"
    r"kg|mg|µg|ng|g|m|cm|mm|km|nm|µm|L|mL|dL|µL|"
    r"s|ms|min|h|Hz|kHz|MHz|GHz|"
    r"mol|mmol|µmol|pmol|"
    r"Pa|kPa|MPa|bar|psi|"
    r"J|kJ|MJ|kWh|Wh|W|kW|MW|"
    r"N|kN|"
    r"°C|°F|K|"
    r"mol/L|mg/dL|g/L|mEq/L|U/L|"
    r"cd/m²|lx|"
    r"m/s|m/s²|km/h|"
    r"px|pt|dpi"
    r")(?![\w])"
)
_STATISTIC_RE = re.compile(
    r"(?<![\w.,])\d+(?:[.,]\d+)?\s*%?\s*(?:±|\+/-|\+-)\s*\d+(?:[.,]\d+)?\s*%?"
)
_YEAR_RE = re.compile(r"(?<![\w])((?:19|20)\d{2})(?![\w])")
_DATE_RE = re.compile(
    r"(?<![\w])\d{1,2}/\d{1,2}/\d{2,4}(?![\w])"
    r"|(?<![\w])\d{4}-\d{2}-\d{2}(?![\w])"
    r"|(?<![\w])\d{1,2}\s+de\s+[A-Za-zÀ-ÿ]{3,}\s+de\s+\d{4}(?![\w])"
)
_QUOTE_RE = re.compile(r"[“”„‟«»‹›](?:[^“”„‟«»‹›]{1,800}?)[“”„‟«»‹›]")
_CITATION_NUM_RE = re.compile(r"\[\d+(?:\s*[-–,;]\s*\d+)*\]")
_PAREN_RE = re.compile(r"\(([^()]{3,160})\)")
_YEAR_IN_TEXT_RE = re.compile(r"\b(?:19|20)\d{2}[a-z]?\b")
_SURNAME_RE = re.compile(r"[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][\wÀ-ÿ'’-]+")
_SUBSCRIPT_RE = re.compile(r"(?<=[A-Za-zÀ-ÿ])\s+_[A-Za-z0-9]")
_TABLE_ID_RE = re.compile(r"(?<![\w])(?:Tabela|Quadro|Figure|Table)\s+\d+(?:\.\d+)?(?![\w])")
_FIGURE_ID_RE = re.compile(r"(?<![\w])(?:Figura|Fig\.?|Gráfico|Image)\s+\d+(?:\.\d+)?(?![\w])")
_REFERENCES_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:refer[eê]ncias|refer[eê]ncias bibliogr[aá]ficas|bibliografia)\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_REFERENCE_LINE_RE = re.compile(
    r"^\s*[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][\wÀ-ÿ'’-]+(?:,\s*[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ]\.(?:\s*[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ]\.)*)?"
    r".*\b(?:19|20)\d{2}\b"
)

#: Caracteres que indicam notação matemática dentro de um token.
_MATH_RANGES: tuple[tuple[int, int], ...] = (
    (0x00B1, 0x00B1),  # ±
    (0x00B7, 0x00B7),  # · (ponto de multiplicação)
    (0x00B2, 0x00B3),  # ² ³
    (0x00B9, 0x00B9),  # ¹
    (0x00D7, 0x00D7),  # ×
    (0x00F7, 0x00F7),  # ÷
    (0x0370, 0x03FF),  # alfabeto grego
    (0x1F00, 0x1FFF),  # grego politônico
    (0x2070, 0x207F),  # superíndices
    (0x2080, 0x209C),  # subscritos
    (0x2100, 0x214F),  # letras e símbolos
    (0x2190, 0x21FF),  # setas
    (0x2200, 0x22FF),  # operadores matemáticos
    (0x27C0, 0x27EF),  # operadores matemáticos adicionais
    (0x27F0, 0x27FF),  # setas longas
    (0x2980, 0x29FF),  # operadores de conjunto
    (0x2A00, 0x2AFF),  # operadores supplemental
    (0x1D2C, 0x1DBF),  # superíndices e subscritos tipográficos
)


def is_math_char(char: str) -> bool:
    """Indica se o caractere participa de notação matemática."""
    ponto = ord(char)
    return any(inicio <= ponto <= fim for inicio, fim in _MATH_RANGES)


def _tokens_com_matematica(texto: str) -> Iterator[tuple[int, int]]:
    """Percorre os tokens (sem espaços) que contenham notação matemática.

    A pontuação que encosta no token (``m².``, ``(α)``) fica de fora do
    intervalo protegido, para que as regras de pontuação continuem valendo
    sobre ela.
    """
    inicio_token = 0
    tamanho = len(texto)
    indice = 0
    while indice < tamanho:
        char = texto[indice]
        if char.isspace():
            if indice > inicio_token:
                token = texto[inicio_token:indice]
                if any(is_math_char(c) for c in token):
                    inicio, fim = _recortar_token(texto, inicio_token, indice)
                    yield inicio, fim
            indice += 1
            inicio_token = indice
            continue
        indice += 1
    if tamanho > inicio_token:
        token = texto[inicio_token:tamanho]
        if any(is_math_char(c) for c in token):
            inicio, fim = _recortar_token(texto, inicio_token, tamanho)
            yield inicio, fim


def _recortar_token(texto: str, inicio: int, fim: int) -> tuple[int, int]:
    """Remove a pontuação que encosta no token matemático."""
    while inicio < fim and texto[inicio] in "([{«“‘":
        inicio += 1
    while fim > inicio and texto[fim - 1] in ".,;:!?)]}»”’":
        fim -= 1
    return inicio, fim


def _linhas_de_tabela(texto: str) -> Iterator[tuple[int, int]]:
    """Percorre os blocos de linhas que parecem tabela.

    Uma linha pertence a uma tabela quando contém dois ou mais ``|`` ou
    caracteres de desenho de caixa. Blocos de duas ou mais linhas consecutivas
    são protegidos como tabela.
    """
    deslocamento = 0
    bloco_inicio: int | None = None
    for linha in texto.splitlines(keepends=True):
        conteudo = linha.rstrip("\r\n")
        tem_vertical = conteudo.count("|") >= 2
        tem_caixa = sum(1 for c in conteudo if _is_box_drawing(c)) >= 2
        if tem_vertical or tem_caixa:
            if bloco_inicio is None:
                bloco_inicio = deslocamento
        else:
            if bloco_inicio is not None and deslocamento - bloco_inicio > 0:
                linhas = texto[bloco_inicio:deslocamento].count("\n") + 1
                if linhas >= 2:
                    yield bloco_inicio, deslocamento
            bloco_inicio = None
        deslocamento += len(linha)
    if bloco_inicio is not None and deslocamento > bloco_inicio:
        linhas = texto[bloco_inicio:deslocamento].count("\n") + 1
        if linhas >= 2:
            yield bloco_inicio, deslocamento


def _is_box_drawing(char: str) -> bool:
    ponto = ord(char)
    return 0x2500 <= ponto <= 0x257F


def _bloco_de_referencias(texto: str) -> Iterator[tuple[int, int]]:
    """Percorre as linhas de referência da lista de referências, se houver."""
    cabecalho = _REFERENCES_HEADING_RE.search(texto)
    if cabecalho is None:
        return
    deslocamento = cabecalho.end()
    # Avança para o início da linha seguinte ao cabeçalho.
    fim_linha = texto.find("\n", deslocamento)
    if fim_linha != -1:
        deslocamento = fim_linha + 1
    for linha in texto[deslocamento:].splitlines(keepends=True):
        if not linha.strip():
            break
        if _REFERENCE_LINE_RE.match(linha):
            yield deslocamento, deslocamento + len(linha)
        deslocamento += len(linha)


def _spans_de_um_detalhe(
    texto: str,
    expressao: re.Pattern[str],
    tipo: ProtectedKind,
) -> Iterator[ProtectedSpan]:
    for match in expressao.finditer(texto):
        yield ProtectedSpan(match.start(), match.end(), tipo)


def detect_protected_spans(texto: str) -> list[ProtectedSpan]:
    """Detecta os intervalos protegidos do texto.

    Os intervalos são devolvidos ordenados, sem sobreposição e sem
    sobreposição parcial entre categorias.
    """
    candidatos: list[ProtectedSpan] = []

    candidatos.extend(_spans_de_um_detalhe(texto, _FENCED_CODE_RE, ProtectedKind.CODE))
    candidatos.extend(_spans_de_um_detalhe(texto, _INLINE_CODE_RE, ProtectedKind.CODE))
    candidatos.extend(_spans_de_um_detalhe(texto, _DOI_RE, ProtectedKind.DOI))
    candidatos.extend(_spans_de_um_detalhe(texto, _URL_RE, ProtectedKind.URL))
    candidatos.extend(_spans_de_um_detalhe(texto, _QUOTE_RE, ProtectedKind.QUOTE_LITERAL))
    candidatos.extend(_spans_de_um_detalhe(texto, _CITATION_NUM_RE, ProtectedKind.CITATION))
    candidatos.extend(_spans_de_um_detalhe(texto, _STATISTIC_RE, ProtectedKind.STATISTIC))
    candidatos.extend(_spans_de_um_detalhe(texto, _DATE_RE, ProtectedKind.DATE))
    candidatos.extend(_spans_de_um_detalhe(texto, _NUMBER_RE, ProtectedKind.NUMBER))
    candidatos.extend(_spans_de_um_detalhe(texto, _UNIT_RE, ProtectedKind.UNIT))
    candidatos.extend(_spans_de_um_detalhe(texto, _YEAR_RE, ProtectedKind.DATE))
    candidatos.extend(_spans_de_um_detalhe(texto, _TABLE_ID_RE, ProtectedKind.TABLE_ID))
    candidatos.extend(_spans_de_um_detalhe(texto, _FIGURE_ID_RE, ProtectedKind.FIGURE_ID))

    for inicio, fim in _linhas_de_tabela(texto):
        candidatos.append(ProtectedSpan(inicio, fim, ProtectedKind.TABLE))

    for inicio, fim in _bloco_de_referencias(texto):
        candidatos.append(ProtectedSpan(inicio, fim, ProtectedKind.REFERENCE))

    for inicio, fim in _tokens_com_matematica(texto):
        candidatos.append(ProtectedSpan(inicio, fim, ProtectedKind.FORMULA))

    for match in _SUBSCRIPT_RE.finditer(texto):
        candidatos.append(ProtectedSpan(match.start() + 1, match.end(), ProtectedKind.FORMULA))

    for match in _PAREN_RE.finditer(texto):
        conteudo = match.group(1)
        tem_ano = _YEAR_IN_TEXT_RE.search(conteudo) is not None
        tem_sobrenome = _SURNAME_RE.search(conteudo) is not None
        if tem_ano and tem_sobrenome:
            candidatos.append(ProtectedSpan(match.start(), match.end(), ProtectedKind.CITATION))

    return _resolver_sobreposicoes(candidatos)


def _resolver_sobreposicoes(candidatos: list[ProtectedSpan]) -> list[ProtectedSpan]:
    """Resolve sobreposições mantendo a categoria de maior prioridade."""
    ordenados = sorted(
        candidatos,
        key=lambda span: (_PRIORIDADE.get(span.kind, 99), span.start, -(span.end - span.start)),
    )
    aceitos: list[ProtectedSpan] = []
    for span in ordenados:
        if any(span.overlaps(existente) for existente in aceitos):
            continue
        aceitos.append(span)
    return sorted(aceitos, key=lambda span: span.start)


def free_spans(texto: str, protegidos: list[ProtectedSpan]) -> list[tuple[int, int]]:
    """Devolve os intervalos do texto **não** cobertos pela proteção.

    São eles que o motor pode alterar.
    """
    livres: list[tuple[int, int]] = []
    cursor = 0
    for span in protegidos:
        if span.start > cursor:
            livres.append((cursor, span.start))
        cursor = max(cursor, span.end)
    if cursor < len(texto):
        livres.append((cursor, len(texto)))
    return livres


def build_catalog(texto: str) -> ProtectionCatalog:
    """Extrai o catálogo de entidades protegidas do texto.

    Cada entidade recebe um identificador estável (``P0001``), o nível de
    proteção definido pela categoria e o *fingerprint* usado para verificar,
    em ondas posteriores, que o valor não foi alterado.
    """
    entidades: list[ProtectedEntity] = []
    for indice, span in enumerate(detect_protected_spans(texto), start=1):
        trecho = texto[span.start : span.end]
        entidades.append(
            ProtectedEntity(
                id=f"P{indice:04d}",
                kind=span.kind,
                text=trecho,
                source_range=SourceRange(start=span.start, end=span.end),
                level=default_level(span.kind),
                fingerprint=fingerprint(trecho),
                rule_id=f"{RULE_ID_PREFIX}.{span.kind}",
            )
        )
    return ProtectionCatalog(entities=tuple(entidades))
