"""Análise textual pré-humanização.

Identifica, de forma determinística, padrões que prejudicam a clareza e a
naturalidade: repetições, frases padronizadas, transições artificiais,
vagueza, redundância, voz passiva e excesso de conectivos. O resultado orienta
a reescrita e é exibido no relatório da interface.
"""

from __future__ import annotations

import re
from collections import Counter

from pydantic import BaseModel, ConfigDict

#: Palavras sem valor semântico, ignoradas na contagem de repetições.
_STOPWORDS = frozenset(
    {
        "de",
        "a",
        "o",
        "e",
        "que",
        "do",
        "da",
        "em",
        "um",
        "uma",
        "para",
        "com",
        "não",
        "se",
        "na",
        "no",
        "os",
        "as",
        "dos",
        "das",
        "por",
        "ao",
        "à",
        "é",
        "como",
        "mais",
        "foi",
        "ser",
        "ou",
        "são",
        "entre",
        "sobre",
        "também",
        "já",
        "muito",
        "até",
        "sem",
        "mas",
        "seu",
        "sua",
        "eles",
        "elas",
        "nos",
    }
)

#: Frases padronizadas (chavões acadêmicos).
_FRASES_PADRONIZADAS = (
    "é importante ressaltar que",
    "vale destacar que",
    "é válido ressaltar",
    "diante do exposto",
    "pode-se afirmar que",
    "cabe ressaltar que",
    "convém destacar que",
    "é notório que",
    "não obstante",
    "dessa forma",
    "face ao exposto",
    "ante o exposto",
)

#: Transições artificiais (sequências mecânicas).
_TRANSICOES_ARTIFICIAIS = (
    "primeiramente",
    "segundamente",
    "terceiramente",
    "em primeiro lugar",
    "em segundo lugar",
    "em terceiro lugar",
    "por fim",
    "por último",
)

#: Termos vagos.
_VAGUIDADE = (
    "muito",
    "bastante",
    "coisa",
    "algo",
    "diversos",
    "vários",
    "alguns",
    "algumas",
    "certo",
    "certa",
    "determinado",
    "determinada",
)

#: Redundâncias comuns (verbo de movimento + direção redundante).
_REDUNDANCIA: tuple[tuple[str, str], ...] = (
    (r"\b(?:subir|subiu|sobe|subindo)\b[^.!?]*\bpara cima\b", "subir para cima"),
    (r"\b(?:descer|desceu|desce|descendo)\b[^.!?]*\bpara baixo\b", "descer para baixo"),
    (r"\b(?:entrar|entrou|entra|entrando)\b[^.!?]*\bpara dentro\b", "entrar para dentro"),
    (r"\b(?:sair|saiu|sai|saindo)\b[^.!?]*\bpara fora\b", "sair para fora"),
)

#: Marcas de voz passiva.
_VOZ_PASSIVA_RE = re.compile(
    r"\b(?:foi|foram|é|são|será|serão|era|eram|está|estão|estava|estavam)\s+"
    r"(?:realizado|realizada|realizados|realizadas|analisado|analisada|analisados|analisadas|"
    r"considerado|considerada|considerados|consideradas|discutido|discutida|discutidos|discutidas|"
    r"observado|observada|observados|observadas|verificado|verificada|verificados|verificadas|"
    r"desenvolvido|desenvolvida|desenvolvidos|desenvolvidas|utilizado|utilizada|utilizados|utilizadas)\b"
)

#: Conectivos para a medição de excesso.
_CONECTIVOS = (
    "portanto",
    "contudo",
    "todavia",
    "entretanto",
    "ademais",
    "no entanto",
    "assim",
    "porém",
    "logo",
    "pois",
    "embora",
    "não obstante",
)


class AnalysisReport(BaseModel):
    """Resultado da análise textual."""

    model_config = ConfigDict(frozen=True)

    repeticoes: tuple[str, ...] = ()
    """Palavras repetidas em excesso (3+ ocorrências)."""

    frases_padronizadas: tuple[str, ...] = ()
    """Chavões e frases padronizadas encontradas."""

    transicoes_artificiais: tuple[str, ...] = ()
    """Transições mecânicas encontradas."""

    coesao: str = "boa"
    """Avaliação qualitativa: ``boa`` | ``regular`` | ``a melhorar``."""

    vaguidade: tuple[str, ...] = ()
    """Termos vagos encontrados."""

    redundancia: tuple[str, ...] = ()
    """Redundâncias encontradas."""

    voz_passiva: tuple[str, ...] = ()
    """Trechos em voz passiva."""

    excesso_conectivos: tuple[str, ...] = ()
    """Conectivos em excesso."""


def analyze(texto: str) -> AnalysisReport:
    """Analisa o texto e devolve o relatório."""
    minusculo = texto.lower()
    palavras = re.findall(r"\w+", minusculo)
    relevantes = [p for p in palavras if p not in _STOPWORDS and len(p) > 2]

    contagem = Counter(relevantes)
    repeticoes = tuple(palavra for palavra, n in contagem.items() if n >= 3)

    frases_padronizadas = tuple(f for f in _FRASES_PADRONIZADAS if f in minusculo)
    transicoes = tuple(t for t in _TRANSICOES_ARTIFICIAIS if t in minusculo)
    vaguidade = tuple(v for v in _VAGUIDADE if re.search(rf"\b{re.escape(v)}\b", minusculo))
    redundancia = tuple(rotulo for padrao, rotulo in _REDUNDANCIA if re.search(padrao, minusculo))
    voz_passiva = tuple(m.group(0) for m in _VOZ_PASSIVA_RE.finditer(texto))

    conectivos_presentes = [c for c in _CONECTIVOS if re.search(rf"\b{re.escape(c)}\b", minusculo)]
    n_frases = max(len(re.findall(r"[.!?]+", texto)), 1)
    excesso = tuple(conectivos_presentes) if len(conectivos_presentes) / n_frases > 0.8 else ()

    return AnalysisReport(
        repeticoes=repeticoes,
        frases_padronizadas=frases_padronizadas,
        transicoes_artificiais=transicoes,
        coesao=_coesao(len(conectivos_presentes), n_frases),
        vaguidade=vaguidade,
        redundancia=redundancia,
        voz_passiva=voz_passiva,
        excesso_conectivos=excesso,
    )


def _coesao(conectivos: int, frases: int) -> str:
    if conectivos == 0 and frases > 2:
        return "a melhorar"
    if conectivos / max(frases, 1) < 0.3:
        return "regular"
    return "boa"
