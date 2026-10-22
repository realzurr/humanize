"""Testes de leitura de configuração a partir de variáveis de ambiente."""

from __future__ import annotations

import pytest

from app.core.config import Settings


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("chave-a,chave-b", ["chave-a", "chave-b"]),
        (" chave-a , ,chave-b ", ["chave-a", "chave-b"]),
        ('["chave-a", "chave-b"]', ["chave-a", "chave-b"]),
        ("", []),
    ],
)
def test_chaves_anteriores_aceitam_csv_json_e_vazio(
    monkeypatch: pytest.MonkeyPatch, valor: str, esperado: list[str]
) -> None:
    monkeypatch.setenv("PREVIOUS_SECRET_KEYS", valor)
    monkeypatch.setenv("PREVIOUS_ENCRYPTION_KEYS", valor)

    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.previous_secret_keys == esperado
    assert settings.previous_encryption_keys == esperado


def test_rate_limit_backend_desconhecido_e_rejeitado(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "memcached")
    with pytest.raises(ValueError, match="rate_limit_backend"):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_create_app_com_redis_sem_url_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings
    from app.main import create_app

    monkeypatch.setenv("RATE_LIMIT_BACKEND", "redis")
    monkeypatch.delenv("REDIS_URL", raising=False)
    get_settings.cache_clear()
    try:
        with pytest.raises(ValueError, match="REDIS_URL"):
            create_app()
    finally:
        get_settings.cache_clear()


def test_create_app_com_redis_usa_limitador_compartilhado(monkeypatch: pytest.MonkeyPatch) -> None:
    import fakeredis

    from app import main
    from app.core.config import get_settings
    from app.core.ratelimit import RedisSlidingWindowLimiter

    monkeypatch.setenv("RATE_LIMIT_BACKEND", "redis")
    monkeypatch.setenv("REDIS_URL", "redis://fake:6379/0")
    monkeypatch.setattr(main, "connect_redis", lambda _url: fakeredis.FakeRedis())
    get_settings.cache_clear()
    try:
        app = main.create_app()
    finally:
        get_settings.cache_clear()

    assert isinstance(app.state.rate_limiters["login"], RedisSlidingWindowLimiter)
    assert isinstance(app.state.rate_limiters["humanize"], RedisSlidingWindowLimiter)
