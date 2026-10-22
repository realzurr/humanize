"""Validação e extração seguras de uploads de documentos.

Garante: limite de tamanho, validação do tipo real (magic bytes) e ausência de
path traversal via sanitização do nome e verificação de caminho final. Apenas
formatos textuais (UTF-8) e DOCX são aceitos.
"""

from __future__ import annotations

import os
import re
from io import BytesIO

from docx import Document as DocxDocument

from app.core.errors import LimitExceededError, ValidationError

TEXT_EXTENSIONS = frozenset({".txt", ".md", ".markdown", ".bib", ".csl", ".json", ".csv"})
DOCX_EXTENSIONS = frozenset({".docx"})
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | DOCX_EXTENSIONS

_DOCX_MAGIC = b"PK\x03\x04"

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(name: str) -> str:
    """Sanitiza o nome do arquivo: só basename, sem separadores ou ``..``."""
    base = os.path.basename(name.replace("\\", "/"))
    stem, ext = os.path.splitext(base)
    stem = _SAFE_NAME_RE.sub("_", stem).strip("._") or "arquivo"
    return f"{stem[:100]}{ext.lower()[:10]}"


def detect_format(filename: str, data: bytes) -> str:
    """Determina o formato a partir da extensão e dos magic bytes."""
    ext = os.path.splitext(filename)[1].lower()
    if ext in DOCX_EXTENSIONS:
        if not data.startswith(_DOCX_MAGIC):
            raise ValidationError("arquivo .docx inválido (não é um documento DOCX)")
        return "docx"
    if ext in TEXT_EXTENSIONS:
        return "text"
    raise ValidationError(f"formato não suportado: {ext or '(sem extensão)'}")


def extract_text(filename: str, data: bytes) -> str:
    """Extrai o texto do upload (UTF-8 para textuais, parágrafos para DOCX)."""
    fmt = detect_format(filename, data)
    if fmt == "docx":
        return _extract_docx_text(data)
    return _decode_text(data)


def _decode_text(data: bytes) -> str:
    if b"\x00" in data:
        raise ValidationError("arquivo binário não suportado")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError("arquivo não é texto UTF-8 válido") from exc


def _extract_docx_text(data: bytes) -> str:
    try:
        documento = DocxDocument(BytesIO(data))
    except Exception as exc:  # pragma: no cover - python-docx pode lançar exceções variadas
        raise ValidationError("não foi possível ler o DOCX") from exc
    paragrafos = [p.text for p in documento.paragraphs if p.text.strip()]
    return "\n".join(paragrafos)


def validate_size(data: bytes, *, max_bytes: int) -> None:
    """Rejeita uploads acima do limite."""
    if len(data) > max_bytes:
        raise LimitExceededError(f"arquivo excede o limite de {max_bytes} bytes")


def store_upload(storage_dir: str, filename: str, data: bytes) -> str:
    """Grava o upload num caminho seguro dentro de ``storage_dir``.

    Defesa em profundidade: mesmo com o nome já sanitizado, o caminho final é
    resolvido e validado contra o diretório de armazenamento.
    """
    raiz = os.path.abspath(storage_dir)
    destino = os.path.abspath(os.path.join(raiz, filename))
    if not destino.startswith(raiz + os.sep):
        raise ValidationError("nome de arquivo inválido")
    os.makedirs(raiz, exist_ok=True)
    with open(destino, "wb") as arquivo:
        arquivo.write(data)
    return destino
