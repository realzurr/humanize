"""Agregador de rotas da API v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import health, normalize

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(normalize.router)
