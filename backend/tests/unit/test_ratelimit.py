"""Testes do limitador de janela deslizante."""

from __future__ import annotations

from app.core.ratelimit import SlidingWindowLimiter


def test_permite_dentro_do_limite() -> None:
    limiter = SlidingWindowLimiter(limit=3, window_seconds=60)
    assert limiter.allow("cliente-1")
    assert limiter.allow("cliente-1")
    assert limiter.allow("cliente-1")


def test_bloqueia_acima_do_limite() -> None:
    limiter = SlidingWindowLimiter(limit=2, window_seconds=60)
    assert limiter.allow("cliente-1")
    assert limiter.allow("cliente-1")
    assert not limiter.allow("cliente-1")


def test_limite_por_chave_independe() -> None:
    limiter = SlidingWindowLimiter(limit=1, window_seconds=60)
    assert limiter.allow("cliente-1")
    assert limiter.allow("cliente-2")
    assert not limiter.allow("cliente-1")
