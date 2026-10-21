"""Agregador de rotas da API v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import academic, health, humanize, normalize, providers, templates

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(normalize.router)
api_router.include_router(providers.router)
api_router.include_router(humanize.router)
api_router.include_router(templates.router)
api_router.include_router(academic.router)
