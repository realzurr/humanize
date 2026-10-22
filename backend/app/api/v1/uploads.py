"""Rota de upload seguro de documentos (v1).

Valida o tamanho, o tipo real (magic bytes) e o nome do arquivo, e armazena
num caminho seguro (sem path traversal e sem colisão de nomes), isolado por
usuário quando a autenticação está ativa. A extração de DOCX (CPU-bound) roda
fora do event loop.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile

from app.api.deps import get_current_user, owner_id_of
from app.core.config import Settings
from app.models._util import new_id
from app.models.user import User
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
    usuario: Annotated[User | None, Depends(get_current_user)],
) -> UploadResponse:
    """Recebe um arquivo, valida e devolve o texto extraído + metadados seguros."""
    settings: Settings = request.app.state.settings
    dados = await arquivo.read()
    nome_original = arquivo.filename or "arquivo.txt"

    validate_size(dados, max_bytes=settings.max_upload_bytes)
    sanitizado = sanitize_filename(nome_original)
    formato = detect_format(nome_original, dados)

    # A extração (especialmente DOCX via python-docx) é CPU-bound: fora do loop.
    texto = await asyncio.to_thread(extract_text, nome_original, dados)

    # Prefixa com um id único para evitar colisão de nomes entre uploads (GAP-05)
    # e isola por dono quando a autenticação está ativa (GAP-03).
    upload_id = new_id()
    nome_armazenado = f"{upload_id}_{sanitizado}"
    dono_dir = owner_id_of(usuario) or "local"
    store_upload(str(settings.storage_dir / "uploads" / dono_dir), nome_armazenado, dados)

    return UploadResponse(
        id=upload_id,
        filename=sanitizado,
        format=formato,
        size_bytes=len(dados),
        texto=texto,
    )
