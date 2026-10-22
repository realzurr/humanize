"""Utilitários compartilhados pelos modelos ORM."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def new_id() -> str:
    """Identificador primário curto (32 hex, sem hífen)."""
    return uuid4().hex


def utcnow() -> datetime:
    """Instante atual em UTC, sem informação de fuso (compatível com SQLite)."""
    return datetime.now(UTC).replace(tzinfo=None)
