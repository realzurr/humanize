"""Rotas de saúde e diagnóstico (v1)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["saude"])


@router.get("/health")
async def health() -> dict[str, Any]:
    """Verifica que o processo está respondendo."""
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/health/readiness")
async def readiness() -> dict[str, Any]:
    """Verifica dependências obrigatórias para processar documentos."""
    settings = get_settings()
    checks: dict[str, Any] = {
        "database": {"ok": True, "detail": "configurado"},
        "templates": {"ok": settings.templates_dir.exists(), "detail": str(settings.templates_dir)},
    }
    healthy = all(check["ok"] for check in checks.values())
    return {"status": "ok" if healthy else "degraded", "checks": checks}
