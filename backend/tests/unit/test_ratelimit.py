"""Testes do limitador de janela deslizante."""

from __future__ import annotations

import os
import secrets
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from typing import Any, cast

import fakeredis
import pytest
from starlette.requests import Request

from app.core.ratelimit import (
    RedisSlidingWindowLimiter,
    SlidingWindowLimiter,
    SqliteSlidingWindowLimiter,
    build_rate_limiter,
    client_ip,
    connect_redis,
)


def _request(xff: str | None, host: str = "10.0.0.2") -> Request:
    headers = [] if xff is None else [(b"x-forwarded-for", xff.encode())]
    return Request({"type": "http", "headers": headers, "client": (host, 1234)})


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


def test_sqlite_sliding_window_limiter_compartilhado_entre_instancias(tmp_path: Path) -> None:
    db_file = tmp_path / "ratelimit.db"
    worker_a = build_rate_limiter(
        limit=2, window_seconds=60, backend="sqlite", namespace="login", sqlite_path=db_file
    )
    worker_b = SqliteSlidingWindowLimiter(db_file, namespace="login", limit=2, window_seconds=60)

    assert worker_a.allow("10.0.0.1") is True
    assert worker_b.allow("10.0.0.1") is True
    assert worker_a.allow("10.0.0.1") is False
    assert worker_b.allow("10.0.0.1") is False


def test_redis_sliding_window_limiter_com_lua_real() -> None:
    cliente = fakeredis.FakeRedis()
    limiter = RedisSlidingWindowLimiter(cliente, namespace="humanize", limit=2, window_seconds=60)
    assert limiter.allow("ip-1") is True
    assert limiter.allow("ip-1") is True
    assert limiter.allow("ip-1") is False
    assert limiter.allow("ip-2") is True
    assert 0 < cliente.ttl("ratelimit:humanize:ip-1") <= 61


def test_redis_compartilha_limite_entre_nos() -> None:
    servidor = fakeredis.FakeServer()
    no_a = RedisSlidingWindowLimiter(
        fakeredis.FakeRedis(server=servidor), namespace="login", limit=2, window_seconds=60
    )
    no_b = RedisSlidingWindowLimiter(
        fakeredis.FakeRedis(server=servidor), namespace="login", limit=2, window_seconds=60
    )
    assert no_a.allow("10.0.0.1") is True
    assert no_b.allow("10.0.0.1") is True
    assert no_a.allow("10.0.0.1") is False
    assert no_b.allow("10.0.0.1") is False


def test_redis_concorrencia_nao_ultrapassa_limite() -> None:
    servidor = fakeredis.FakeServer()
    limiters = [
        RedisSlidingWindowLimiter(
            fakeredis.FakeRedis(server=servidor), namespace="c", limit=5, window_seconds=60
        )
        for _ in range(4)
    ]
    with ThreadPoolExecutor(max_workers=8) as pool:
        resultados = list(pool.map(lambda i: limiters[i % 4].allow("ip"), range(40)))
    assert sum(resultados) == 5


def test_connect_redis_exige_url() -> None:
    with pytest.raises(ValueError, match="REDIS_URL"):
        connect_redis("")


def test_build_rate_limiter_redis_sem_cliente_falha() -> None:
    with pytest.raises(ValueError, match="redis_client"):
        build_rate_limiter(limit=1, window_seconds=60, backend="redis")


def test_build_rate_limiter_sqlite_sem_caminho_falha() -> None:
    with pytest.raises(ValueError, match="sqlite_path"):
        build_rate_limiter(limit=1, window_seconds=60, backend="sqlite")


def test_sqlite_poda_global_remove_chaves_abandonadas(tmp_path: Path) -> None:
    db_file = tmp_path / "ratelimit.db"
    limiter = SqliteSlidingWindowLimiter(db_file, limit=5, window_seconds=0.0)
    limiter.allow("cliente-que-nao-volta")
    for _ in range(SqliteSlidingWindowLimiter._GLOBAL_PRUNE_EVERY):
        limiter.allow("outro-cliente")

    with closing(sqlite3.connect(db_file)) as conn:
        restantes = conn.execute(
            "SELECT COUNT(*) FROM rate_limit_hits WHERE client_key = ?",
            ("cliente-que-nao-volta",),
        ).fetchone()[0]
    assert restantes == 0


def test_client_ip_usa_entrada_anexada_pelo_proxy() -> None:
    requisicao = _request("1.2.3.4, 198.51.100.7")
    assert client_ip(requisicao, trust_proxy=True) == "198.51.100.7"


def test_client_ip_respeita_quantidade_de_proxies_confiaveis() -> None:
    requisicao = _request("1.2.3.4, 198.51.100.7, 10.0.0.9")
    assert client_ip(requisicao, trust_proxy=True, trusted_hops=2) == "198.51.100.7"
    assert client_ip(requisicao, trust_proxy=True, trusted_hops=10) == "1.2.3.4"


def test_client_ip_ignora_cabecalho_sem_proxy_confiavel() -> None:
    requisicao = _request("1.2.3.4")
    assert client_ip(requisicao, trust_proxy=False) == "10.0.0.2"


@pytest.mark.integration
def test_redis_real_quando_disponivel() -> None:
    """Executa contra um Redis real se ``REDIS_TEST_URL`` estiver definida (opcional)."""
    url = os.environ.get("REDIS_TEST_URL")
    if not url:
        pytest.skip("REDIS_TEST_URL não definida")
    cliente = connect_redis(url)
    namespace = f"teste-{secrets.token_hex(4)}"
    limiters = [
        RedisSlidingWindowLimiter(
            connect_redis(url), namespace=namespace, limit=5, window_seconds=60
        )
        for _ in range(4)
    ]
    with ThreadPoolExecutor(max_workers=8) as pool:
        resultados = list(pool.map(lambda i: limiters[i % 4].allow("ip"), range(40)))
    assert sum(resultados) == 5
    assert cast(int, cast(Any, cliente).ttl(f"ratelimit:{namespace}:ip")) > 0
