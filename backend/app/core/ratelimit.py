"""Limitação de consumo de API (janela deslizante).

Suporta três backends com o mesmo contrato (:class:`RateLimiter`):

1. ``memory`` (:class:`SlidingWindowLimiter`): em memória por processo (padrão).
2. ``sqlite`` (:class:`SqliteSlidingWindowLimiter`): compartilhado entre
   múltiplos workers no mesmo host via SQLite em modo WAL e transações
   ``BEGIN IMMEDIATE``, sem depender de serviço externo.
3. ``redis`` (:class:`RedisSlidingWindowLimiter`): compartilhado entre múltiplos
   nós via *sorted set*, com limpeza + contagem + inserção num único script Lua
   (atômico no servidor) e relógio do próprio Redis (``ADR-0018``).
"""

from __future__ import annotations

import secrets
import sqlite3
import threading
import time
from collections import deque
from contextlib import closing
from pathlib import Path
from typing import Literal, Protocol, cast, runtime_checkable

from fastapi import Request


@runtime_checkable
class RateLimiter(Protocol):
    """Contrato comum dos limitadores de janela deslizante."""

    def allow(self, key: str) -> bool:
        """Registra uma tentativa e informa se ela está dentro do limite."""


class RedisScriptClient(Protocol):
    """Subconjunto do cliente Redis necessário: execução de script Lua (``EVAL``)."""

    def eval(self, script: str, numkeys: int, *keys_and_args: str) -> object: ...


class SlidingWindowLimiter:
    """Contador de janela deslizante em memória (thread-safe por processo)."""

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


class SqliteSlidingWindowLimiter:
    """Contador de janela deslizante compartilhado via SQLite (múltiplos workers)."""

    #: A cada N chamadas, remove registros expirados de **todas** as chaves, para
    #: que clientes que não voltam não acumulem linhas indefinidamente.
    _GLOBAL_PRUNE_EVERY = 100

    def __init__(
        self,
        db_path: Path,
        *,
        namespace: str = "default",
        limit: int,
        window_seconds: float,
    ) -> None:
        self._db_path = db_path
        self._namespace = namespace
        self._limit = limit
        self._window_seconds = window_seconds
        self._lock = threading.Lock()
        self._calls = 0
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._db_path), timeout=5.0, isolation_level=None)

    def _init_schema(self) -> None:
        # O modo WAL é persistente no arquivo; basta defini-lo uma vez.
        with closing(self._connect()) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS rate_limit_hits ("
                "namespace TEXT NOT NULL, "
                "client_key TEXT NOT NULL, "
                "ts REAL NOT NULL"
                ")"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_rate_limit_ns_key_ts "
                "ON rate_limit_hits (namespace, client_key, ts)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS ix_rate_limit_ts ON rate_limit_hits (ts)")

    def allow(self, key: str) -> bool:
        """Executa limpeza + contagem + inserção atomicamente em transação imediata."""
        now = time.time()
        cutoff = now - self._window_seconds
        with self._lock, closing(self._connect()) as conn:
            self._calls += 1
            poda_global = self._calls % self._GLOBAL_PRUNE_EVERY == 0
            conn.execute("BEGIN IMMEDIATE")
            try:
                if poda_global:
                    conn.execute("DELETE FROM rate_limit_hits WHERE ts <= ?", (cutoff,))
                else:
                    conn.execute(
                        "DELETE FROM rate_limit_hits "
                        "WHERE namespace = ? AND client_key = ? AND ts <= ?",
                        (self._namespace, key, cutoff),
                    )
                row = conn.execute(
                    "SELECT COUNT(*) FROM rate_limit_hits WHERE namespace = ? AND client_key = ?",
                    (self._namespace, key),
                ).fetchone()
                count = int(row[0]) if row is not None else 0
                if count >= self._limit:
                    conn.execute("COMMIT")
                    return False
                conn.execute(
                    "INSERT INTO rate_limit_hits (namespace, client_key, ts) VALUES (?, ?, ?)",
                    (self._namespace, key, now),
                )
                conn.execute("COMMIT")
                return True
            except Exception:
                conn.execute("ROLLBACK")
                raise


#: Executa limpeza, contagem e inserção atomicamente no servidor. Usa ``TIME`` do
#: Redis para que nós com relógios divergentes compartilhem a mesma janela.
_REDIS_SLIDING_WINDOW_LUA = """
local agora_t = redis.call('TIME')
local agora = tonumber(agora_t[1]) + tonumber(agora_t[2]) / 1000000
local janela = tonumber(ARGV[1])
local limite = tonumber(ARGV[2])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', agora - janela)
if redis.call('ZCARD', KEYS[1]) >= limite then
  return 0
end
redis.call('ZADD', KEYS[1], agora, ARGV[3])
redis.call('EXPIRE', KEYS[1], tonumber(ARGV[4]))
return 1
"""


class RedisSlidingWindowLimiter:
    """Contador de janela deslizante sobre Redis, atômico entre nós."""

    def __init__(
        self,
        client: RedisScriptClient,
        *,
        namespace: str = "default",
        limit: int,
        window_seconds: float,
    ) -> None:
        self._client = client
        self._namespace = namespace
        self._limit = limit
        self._window_seconds = window_seconds

    def allow(self, key: str) -> bool:
        redis_key = f"ratelimit:{self._namespace}:{key}"
        ttl = max(1, int(self._window_seconds) + 1)
        membro = secrets.token_hex(8)
        resultado = self._client.eval(
            _REDIS_SLIDING_WINDOW_LUA,
            1,
            redis_key,
            str(self._window_seconds),
            str(self._limit),
            membro,
            str(ttl),
        )
        return bool(int(cast(int, resultado)))


def connect_redis(url: str) -> RedisScriptClient:
    """Cria o cliente Redis a partir da URL (dependência opcional, extra ``redis``)."""
    if not url:
        raise ValueError("RATE_LIMIT_BACKEND=redis exige REDIS_URL")
    try:
        import redis
    except ImportError as exc:  # pragma: no cover - depende do ambiente
        raise ValueError("RATE_LIMIT_BACKEND=redis exige o extra 'redis' instalado") from exc
    return cast(RedisScriptClient, redis.Redis.from_url(url))


def build_rate_limiter(
    *,
    limit: int,
    window_seconds: float,
    backend: Literal["memory", "sqlite", "redis"] = "memory",
    namespace: str = "default",
    sqlite_path: Path | None = None,
    redis_client: RedisScriptClient | None = None,
) -> RateLimiter:
    """Constrói o limitador conforme o backend selecionado.

    Levanta ``ValueError`` quando o backend pedido não pode ser construído, em vez
    de cair silenciosamente para o limite em memória por processo.
    """
    if backend == "sqlite":
        if sqlite_path is None:
            raise ValueError("backend 'sqlite' exige sqlite_path")
        return SqliteSlidingWindowLimiter(
            sqlite_path,
            namespace=namespace,
            limit=limit,
            window_seconds=window_seconds,
        )
    if backend == "redis":
        if redis_client is None:
            raise ValueError("backend 'redis' exige redis_client")
        return RedisSlidingWindowLimiter(
            redis_client,
            namespace=namespace,
            limit=limit,
            window_seconds=window_seconds,
        )
    return SlidingWindowLimiter(limit=limit, window_seconds=window_seconds)


def client_ip(request: Request, *, trust_proxy: bool = False, trusted_hops: int = 1) -> str:
    """Devolve o IP do cliente para fins de limitação.

    ``X-Forwarded-For`` só é considerado quando ``trust_proxy`` é verdadeiro
    (a aplicação está atrás de um proxy reverso confiável); caso contrário,
    usa-se o IP direto da conexão, evitando o bypass por falsificação do
    cabeçalho (`GAP-04`).

    Cada proxy confiável **anexa** o IP que viu ao final do cabeçalho; as
    entradas à esquerda vêm do cliente e são falsificáveis. Por isso o IP real
    é a entrada ``-trusted_hops`` (a mais à direita, com um único proxy).
    """
    if trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            entradas = [item.strip() for item in forwarded.split(",") if item.strip()]
            if entradas:
                return entradas[-min(trusted_hops, len(entradas))]
    if request.client is not None:
        return request.client.host
    return "unknown"
