"""Testes da revogação de tokens persistida no banco."""

from __future__ import annotations

import time

from app.core.security import TokenService
from app.repositories.revocations import SqlRevocationStore

_SEGREDO = "segredo-de-teste-suficientemente-longo-123"


def test_revogacao_sobrevive_a_novo_processo(db_session_factory) -> None:
    processo_a = TokenService(_SEGREDO, revocation_store=SqlRevocationStore(db_session_factory))
    token = processo_a.issue("usuario-1")
    assert processo_a.revoke_token(token) is True

    processo_b = TokenService(_SEGREDO, revocation_store=SqlRevocationStore(db_session_factory))
    assert processo_b.verify(token) is None
    assert processo_b.verify(processo_b.issue("usuario-1")) == "usuario-1"


def test_revogacao_por_usuario_compartilhada(db_session_factory) -> None:
    processo_a = TokenService(_SEGREDO, revocation_store=SqlRevocationStore(db_session_factory))
    processo_b = TokenService(_SEGREDO, revocation_store=SqlRevocationStore(db_session_factory))
    token = processo_a.issue("usuario-2")

    processo_b.revoke_subject("usuario-2")

    assert processo_a.verify(token) is None


def test_prune_remove_revogacoes_inuteis(db_session_factory) -> None:
    store = SqlRevocationStore(db_session_factory)
    agora = time.time()
    store.revoke_jti("expirado", agora - 10)
    store.revoke_jti("vigente", agora + 3600)
    store.revoke_subject("antigo", agora - 7200)
    store.revoke_subject("recente", agora)

    store.prune(now=agora, max_token_age=3600)

    assert not store.is_jti_revoked("expirado")
    assert store.is_jti_revoked("vigente")
    assert store.subject_revoked_before("antigo") is None
    assert store.subject_revoked_before("recente") == agora
