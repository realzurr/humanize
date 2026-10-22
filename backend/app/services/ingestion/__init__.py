"""Serviço de ingestão de documentos (uploads e proteção contra injeção)."""

from app.services.ingestion.guard import INSTRUCAO_SISTEMA, envolver_conteudo
from app.services.ingestion.upload import (
    SUPPORTED_EXTENSIONS,
    extract_text,
    sanitize_filename,
    store_upload,
    validate_size,
)

__all__ = [
    "INSTRUCAO_SISTEMA",
    "SUPPORTED_EXTENSIONS",
    "envolver_conteudo",
    "extract_text",
    "sanitize_filename",
    "store_upload",
    "validate_size",
]
