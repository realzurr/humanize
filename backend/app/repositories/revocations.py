"""Revogações de tokens persistidas no banco (compartilhadas entre workers)."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.revocation import RevokedSubject, RevokedToken


class SqlRevocationStore:
    """Implementação de ``RevocationStore`` sobre SQLAlchemy.

    Recebe a *fábrica* de sessões, e não uma sessão, porque o ``TokenService`` vive
    no estado da aplicação e é usado por requisições concorrentes.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def revoke_jti(self, jti: str, expires_at: float) -> None:
        with self._session_factory() as session:
            session.merge(RevokedToken(jti=jti, expires_at=expires_at))
            session.commit()

    def is_jti_revoked(self, jti: str) -> bool:
        with self._session_factory() as session:
            return session.get(RevokedToken, jti) is not None

    def revoke_subject(self, subject: str, before: float) -> None:
        with self._session_factory() as session:
            session.merge(RevokedSubject(subject=subject, revoked_before=before))
            session.commit()

    def subject_revoked_before(self, subject: str) -> float | None:
        with self._session_factory() as session:
            return session.scalar(
                select(RevokedSubject.revoked_before).where(RevokedSubject.subject == subject)
            )

    def prune(self, *, now: float, max_token_age: float) -> None:
        with self._session_factory() as session:
            session.execute(delete(RevokedToken).where(RevokedToken.expires_at < now))
            session.execute(
                delete(RevokedSubject).where(RevokedSubject.revoked_before < now - max_token_age)
            )
            session.commit()
