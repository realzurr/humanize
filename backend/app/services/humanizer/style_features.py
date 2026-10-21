"""Extração de traços de estilo do texto original.

Traços determinísticos usados para orientar a reescrita e para alimentar a
comparação "antes/depois" da interface. A extração é heurística e serve de
orientação, não de métrica exata.
"""

from __future__ import annotations

import re
import statistics

from pydantic import BaseModel, ConfigDict, Field

#: Conectivos formais (contagem usada para ritmo e construção argumentativa).
_CONECTIVOS = (
    "portanto",
    "contudo",
    "todavia",
    "entretanto",
    "ademais",
    "além disso",
    "dessa forma",
    "desse modo",
    "no entanto",
    "assim",
    "porém",
    "logo",
    "pois",
    "embora",
    "conquanto",
    "outrossim",
    "consoante",
    "destarte",
    "não obstante",
)

#: Marcadores de formalidade.
_FORMAIS = (
    "portanto",
    "entretanto",
    "destarte",
    "consoante",
    "outrossim",
    "no que concerne",
    "outrossim",
)

#: Marcadores de informalidade.
_INFORMAIS = ("tá", "né", "aí", "então", "legal", "bacana", "pra", "cê", "você pode")

#: Termos em latim ou técnicos comuns.
_TERMINOLOGIA = (
    "in vitro",
    "in vivo",
    "in silico",
    "et al.",
    "a priori",
    "a posteriori",
    "ad hoc",
    "per capita",
)

_SENTENCA_RE = re.compile(r"[^.!?]+[.!?]*")


class StyleFeatures(BaseModel):
    """Traços de estilo extraídos do texto."""

    model_config = ConfigDict(frozen=True)

    formalidade: float = Field(ge=0.0, le=1.0)
    """Grau de formalidade estimado (0..1)."""

    vocabulario: str = "comum"
    """``formal`` | ``técnico`` | ``comum``."""

    comprimento_medio_frase: float = 0.0
    """Média de palavras por frase."""

    construcao_argumentativa: str = "simples"
    """``simples`` | ``elaborada`` | ``densa``."""

    conectivos_recorrentes: tuple[str, ...] = ()
    """Conectivos presentes (por frequência decrescente)."""

    terminologia: tuple[str, ...] = ()
    """Termos técnicos e latinismos encontrados."""

    organizacao_paragrafos: str = "simples"
    """``simples`` | ``estruturada`` | ``complexa``."""

    ritmo: str = "regular"
    """``regular`` | ``variado`` | ``irregular``."""


def extract_style_features(texto: str) -> StyleFeatures:
    """Extrai os traços de estilo do texto."""
    frases = _sentencas(texto)
    palavras = re.findall(r"\w+", texto.lower())
    total_palavras = len(palavras)

    comprimento_medio = _media_palavras_por_frase(frases)
    formalidade = _formalidade(palavras)
    conectivos = _conectivos_presentes(texto.lower())
    terminologia = _terminologia_presente(texto.lower())
    ritmo = _ritmo(frases)

    return StyleFeatures(
        formalidade=round(formalidade, 2),
        vocabulario=_vocabulario(formalidade, terminologia),
        comprimento_medio_frase=round(comprimento_medio, 1),
        construcao_argumentativa=_construcao(conectivos, total_palavras),
        conectivos_recorrentes=conectivos,
        terminologia=terminologia,
        organizacao_paragrafos=_organizacao(texto),
        ritmo=ritmo,
    )


def _sentencas(texto: str) -> list[str]:
    return [s.strip() for s in _SENTENCA_RE.findall(texto) if s.strip()]


def _media_palavras_por_frase(frases: list[str]) -> float:
    if not frases:
        return 0.0
    contagens = [len(re.findall(r"\w+", frase)) for frase in frases]
    return statistics.mean(contagens) if contagens else 0.0


def _formalidade(palavras: list[str]) -> float:
    formais = sum(1 for p in palavras if p in _FORMAIS)
    informais = sum(1 for p in palavras if p in _INFORMAIS)
    if formais + informais == 0:
        return 0.5
    return formais / (formais + informais)


def _conectivos_presentes(texto: str) -> tuple[str, ...]:
    contagens = {conectivo: texto.count(conectivo) for conectivo in _CONECTIVOS}
    presentes = sorted(
        (conectivo for conectivo, n in contagens.items() if n > 0),
        key=lambda c: contagens[c],
        reverse=True,
    )
    return tuple(presentes)


def _terminologia_presente(texto: str) -> tuple[str, ...]:
    return tuple(termo for termo in _TERMINOLOGIA if termo in texto)


def _vocabulario(formalidade: float, terminologia: tuple[str, ...]) -> str:
    if terminologia:
        return "técnico"
    if formalidade >= 0.6:
        return "formal"
    return "comum"


def _construcao(conectivos: tuple[str, ...], total_palavras: int) -> str:
    if total_palavras == 0:
        return "simples"
    densidade = len(conectivos) / total_palavras
    if len(conectivos) >= 5 and densidade > 0.01:
        return "densa"
    if len(conectivos) >= 3:
        return "elaborada"
    return "simples"


def _organizacao(texto: str) -> str:
    paragrafos = [p for p in texto.split("\n\n") if p.strip()]
    if len(paragrafos) >= 4:
        return "complexa"
    if len(paragrafos) >= 2:
        return "estruturada"
    return "simples"


def _ritmo(frases: list[str]) -> str:
    if len(frases) < 3:
        return "regular"
    contagens = [len(re.findall(r"\w+", frase)) for frase in frases]
    try:
        desvio = statistics.pstdev(contagens)
    except statistics.StatisticsError:
        return "regular"
    media = statistics.mean(contagens)
    if media == 0:
        return "regular"
    if desvio / media > 0.6:
        return "irregular"
    if desvio / media > 0.35:
        return "variado"
    return "regular"
