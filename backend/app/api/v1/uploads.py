"""Rota de upload seguro de documentos (v1).

Valida o tamanho, o tipo real (magic bytes) e o nome do arquivo, e armazena
num caminho seguro (sem path traversal). O texto extraído é devolvido para o
pipeline de normalização/humanização.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Request, UploadFile

from app.core.config import Settings
from app.models._util import new_id
from app.schemas.uploads import UploadResponse
from app.services.ingestion.upload import (
    detect_format,
    extract_text,
    sanitize_filename,
    store_upload,
    validate_size,
)

router = APIRouter(tags=["uploads"])


@router.post("/uploads", response_model=UploadResponse, status_code=201)
async def upload_documento(
    request: Request,
    arquivo: Annotated[
        UploadFile,
        File(description="Documento .txt, .md, .bib, .csl, .json ou .docx"),
    ],
) -> UploadResponse:
    """Recebe um arquivo, valida e devolve o texto extraído + metadados seguros."""
    settings: Settings = request.app.state.settings
    dados = await arquivo.read()
    nome_original = arquivo.filename or "arquivo.txt"

    validate_size(dados, max_bytes=settings.max_upload_bytes)
    sanitizado = sanitize_filename(nome_original)
    formato = detect_format(nome_original, dados)
    texto = extract_text(nome_original, dados)
    store_upload(str(settings.storage_dir / "uploads"), sanitizado, dados)

    return UploadResponse(
        id=new_id(),
        filename=sanitizado,
        format=formato,
        size_bytes=len(dados),
        texto=texto,
    )
