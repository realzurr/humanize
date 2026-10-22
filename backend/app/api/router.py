"""Agregador de rotas da API v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    academic,
    auth,
    documents,
    exports,
    health,
    humanize,
    normalize,
    providers,
    templates,
    uploads,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(normalize.router)
api_router.include_router(providers.router)
api_router.include_router(humanize.router)
api_router.include_router(templates.router)
api_router.include_router(academic.router)
api_router.include_router(exports.router)
api_router.include_router(auth.router)
api_router.include_router(uploads.router)
api_router.include_router(documents.router)
