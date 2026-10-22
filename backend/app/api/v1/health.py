"""Rotas de saúde e diagnóstico (v1).

Usam ``request.app.state.settings`` (não o cache global ``get_settings()``) e
verificam a conectividade real do banco no ``/health/readiness`` (`GAP-06`).
"""

from __future__ import annotations

import asyncio
from typing import Any, cast

from fastapi import APIRouter, Request
from sqlalchemy import text

from app.core.config import Settings

router = APIRouter(tags=["saude"])


def _settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


@router.get("/health")
async def health(request: Request) -> dict[str, Any]:
    """Verifica que o processo está respondendo."""
    settings = _settings(request)
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/health/readiness")
async def readiness(request: Request) -> dict[str, Any]:
    """Verifica dependências obrigatórias para processar documentos."""
    settings = _settings(request)
    database_ok = await _checar_banco(request)
    templates_ok = settings.templates_dir.exists()

    checks: dict[str, Any] = {
        "database": {
            "ok": database_ok,
            "detail": "conectado" if database_ok else "indisponível",
        },
        "templates": {"ok": templates_ok, "detail": str(settings.templates_dir)},
    }
    healthy = all(check["ok"] for check in checks.values())
    return {"status": "ok" if healthy else "degraded", "checks": checks}


async def _checar_banco(request: Request) -> bool:
    """Verifica a conectividade real com o banco (``SELECT 1``), fora do loop."""

    def _ping() -> bool:
        try:
            with request.app.state.engine.connect() as conexao:
                conexao.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    return await asyncio.to_thread(_ping)
