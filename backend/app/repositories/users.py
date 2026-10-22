"""Repositório de usuários (autenticação)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """Acesso a dados de ``User``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, username: str, password_hash: str) -> User:
        user = User(username=username, password_hash=password_hash)
        self._session.add(user)
        self._session.commit()
        self._session.refresh(user)
        return user

    def get_by_username(self, username: str) -> User | None:
        return self._session.scalar(select(User).where(User.username == username))

    def get(self, user_id: str) -> User | None:
        return self._session.get(User, user_id)
