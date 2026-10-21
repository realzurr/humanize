"""Configuração de logs estruturados.

Logs são emitidos em JSON no formato ``structlog`` para consumo por coletores
de log. **Credenciais nunca são registradas**: o filtro :class:`SecretFilter`
remove chaves conhecidas dos eventos.
"""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog

from app.core.config import Settings, get_settings

#: Padrões de segredo que jamais devem aparecer em log.
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(api[-_]?key|secret|token|password|authorization)\s*[=:]\s*\S+"),
    re.compile(r"(?i)\b(sk-[A-Za-z0-9_\-]{16,}|AIza[A-Za-z0-9_\-]{20,})"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-]{10,}"),
)

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "password",
        "secret",
        "secret_key",
        "token",
        "access_token",
        "refresh_token",
        "x-api-key",
    }
)


def redact(value: str) -> str:
    """Substitui segredos embutidos em texto livre por ``***``."""
    redacted = value
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def redact_secrets(
    logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Processor ``structlog`` que remove segredos dos eventos.

    Substitui o valor de chaves sensíveis por ``***`` e redige segredos
    embutidos em strings livres.

    Devolve **apenas o dicionário de evento**: um processor no meio da
    cadeia precisa devolver o ``event_dict``, não a tupla
    ``(logger, method_name, event_dict)`` — a tupla é a forma de retorno do
    *wrapper* de logger, e devolvê-la aqui corromperia a cadeia.
    """
    cleaned: MutableMapping[str, Any] = {
        key: ("***" if key.lower() in _SENSITIVE_KEYS else value)
        for key, value in event_dict.items()
    }
    for key, value in list(cleaned.items()):
        if isinstance(value, str):
            cleaned[key] = redact(value)
    return cleaned


def configure_logging(settings: Settings | None = None) -> None:
    """Configura o logging estruturado da aplicação."""
    settings = settings or get_settings()

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if settings.debug else logging.INFO,
        force=True,
    )

    renderer = (
        structlog.processors.JSONRenderer()
        if settings.environment in {"production", "test"}
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            redact_secrets,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.debug else logging.INFO
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    """Retorna um logger estruturado com o nome do módulo."""
    return structlog.get_logger(name)
