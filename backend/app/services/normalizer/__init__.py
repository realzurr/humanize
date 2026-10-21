"""Serviço de normalização textual.

Motor **determinístico**: nenhuma regra deste pacote chama LLM, rede ou
serviço externo. O pacote é dividido em:

* :mod:`~app.services.normalizer.engine` — o pipeline;
* :mod:`~app.services.normalizer.rules` — o catálogo de regras;
* :mod:`~app.services.normalizer.protect` — a segmentação do texto em trechos
  protegidos e livres;
* :mod:`~app.services.normalizer.profile` — a configuração por conjunto de regras;
* :mod:`~app.services.normalizer.stats` — o relatório de saída.
"""

from __future__ import annotations

from app.services.normalizer.engine import NormalizationEngine, NormalizationResult
from app.services.normalizer.profile import NormalizationProfile, get_profile
from app.services.normalizer.rules import PIPELINE_ORDER, build_default_rules
from app.services.normalizer.rules.base import NormalizationRule, RuleGroup, RuleOccurrence
from app.services.normalizer.stats import NormalizationReport

__all__ = [
    "PIPELINE_ORDER",
    "NormalizationEngine",
    "NormalizationProfile",
    "NormalizationReport",
    "NormalizationResult",
    "NormalizationRule",
    "RuleGroup",
    "RuleOccurrence",
    "build_default_rules",
    "get_profile",
]
