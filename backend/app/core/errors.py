"""Erros de domínio.

Convertidos em respostas HTTP padronizadas pelo handler registrado em
:mod:`app.main`.
"""

from __future__ import annotations

from typing import Any


class HumanizaError(Exception):
    """Erro base do domínio."""

    code: str = "humaniza_error"
    status_code: int = 400

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_payload(self) -> dict[str, Any]:
        return {"error": {"code": self.code, "message": self.message, "details": self.details}}


class NotFoundError(HumanizaError):
    """Recurso inexistente."""

    code = "not_found"
    status_code = 404


class ValidationError(HumanizaError):
    """Falha de validação de entrada."""

    code = "validation_error"
    status_code = 422


class ProviderUnavailableError(HumanizaError):
    """Provedor de LLM indisponível ou sem credenciais válidas."""

    code = "provider_unavailable"
    status_code = 503


class LimitExceededError(HumanizaError):
    """Limite de uso excedido (tamanho, tokens, requisições)."""

    code = "limit_exceeded"
    status_code = 413


class TemplateError(HumanizaError):
    """Template acadêmico inválido ou incompleto."""

    code = "template_error"
    status_code = 422


class ExportError(HumanizaError):
    """Falha na geração do documento exportado."""

    code = "export_error"
    status_code = 500
