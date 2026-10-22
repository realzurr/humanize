"""Modelos ORM da aplicação.

Importar este pacote registra todos os modelos no ``Base.metadata``, condição
necessária para o ``create_all`` em desenvolvimento e para o autogenerate do
Alembic.
"""

from app.models.credential import ProviderCredential
from app.models.document import Document, DocumentRevision
from app.models.export import Export
from app.models.revocation import RevokedSubject, RevokedToken
from app.models.user import User

__all__ = [
    "Document",
    "DocumentRevision",
    "Export",
    "ProviderCredential",
    "RevokedSubject",
    "RevokedToken",
    "User",
]
