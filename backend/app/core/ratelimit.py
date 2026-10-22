"""Limitação de consumo de API (janela deslizante em memória).

Limita o número de requisições por chave (tipicamente o IP do cliente) numa
janela de tempo, mitigando força bruta e abuso de endpoints custosos. O estado
é em memória — suficiente para uma instância única; um backend compartilhado
(Redis) fica como pendência de produção documentada em ``DEPLOYMENT.md``.
"""

from __future__ import annotations

import threading
import time
from collections import deque

from fastapi import Request


class SlidingWindowLimiter:
    """Contador de janela deslizante por chave."""

    def __init__(self, *, limit: int, window_seconds: float) -> None:
        self._limit = limit
        self._window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """Registra uma tentativa e informa se ela está dentro do limite."""
        now = time.monotonic()
        with self._lock:
            janela = self._hits.setdefault(key, deque())
            while janela and now - janela[0] > self._window_seconds:
                janela.popleft()
            if len(janela) >= self._limit:
                return False
            janela.append(now)
            return True


def client_ip(request: Request, *, trust_proxy: bool = False) -> str:
    """Devolve o IP do cliente para fins de limitação.

    ``X-Forwarded-For`` só é considerado quando ``trust_proxy`` é verdadeiro
    (a aplicação está atrás de um proxy reverso confiável); caso contrário,
    usa-se o IP direto da conexão, evitando o bypass por falsificação do
    cabeçalho (`GAP-04`).
    """
    if trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",", 1)[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"
