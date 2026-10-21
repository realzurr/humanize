"""Humanização semântica por LLM, com preservação de dados protegidos.

O pacote oferece:

* :mod:`~app.services.humanizer.profiles` — 7 perfis autorais;
* :mod:`~app.services.humanizer.intensity` — intensidade (0/25/50/75/100);
* :mod:`~app.services.humanizer.style_features` — traços de estilo;
* :mod:`~app.services.humanizer.analysis` — análise de clareza/coesão;
* :mod:`~app.services.humanizer.engine` — orquestração do ciclo completo.
"""

from __future__ import annotations

from app.services.humanizer.analysis import AnalysisReport, analyze
from app.services.humanizer.engine import HumanizerService, ReviewResult
from app.services.humanizer.intensity import VALID_INTENSITIES, Intensity, validate
from app.services.humanizer.profiles import (
    AUTORAL_ID,
    PROFILES,
    AuthorialProfile,
    build_autoral_profile,
    get_profile,
    list_profiles,
)
from app.services.humanizer.style_features import StyleFeatures, extract_style_features

__all__ = [
    "AUTORAL_ID",
    "PROFILES",
    "VALID_INTENSITIES",
    "AnalysisReport",
    "AuthorialProfile",
    "HumanizerService",
    "Intensity",
    "ReviewResult",
    "StyleFeatures",
    "analyze",
    "build_autoral_profile",
    "extract_style_features",
    "get_profile",
    "list_profiles",
    "validate",
]
