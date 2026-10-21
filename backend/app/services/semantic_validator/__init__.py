"""Validação semântica pós-humanização.

Extrai entidades protegidas, mascara-as antes da chamada ao LLM, restaura os
valores originais depois e compara os catálogos para detectar perda,
alteração e invenção — implementando o portão de aprovação do `ADR-0013`.
"""

from __future__ import annotations

from app.services.semantic_validator.extractor import extract
from app.services.semantic_validator.masker import MaskedText, mask, unmask
from app.services.semantic_validator.validator import (
    FindingCategory,
    Severity,
    ValidationFinding,
    ValidationReport,
    validate,
)

__all__ = [
    "FindingCategory",
    "MaskedText",
    "Severity",
    "ValidationFinding",
    "ValidationReport",
    "extract",
    "mask",
    "unmask",
    "validate",
]
