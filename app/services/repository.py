from __future__ import annotations

import threading
from collections.abc import Iterator
from uuid import UUID

from app.models.document import DocumentRecord


class DocumentRepository:
    """
    In-memory store keyed by document id.

    TODO(security): Replace with Postgres + row-level security on tenant_id.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._by_id: dict[UUID, DocumentRecord] = {}

    def save(self, doc: DocumentRecord) -> None:
        with self._lock:
            self._by_id[doc.id] = doc

    def get(self, doc_id: UUID) -> DocumentRecord | None:
        with self._lock:
            return self._by_id.get(doc_id)

    def iter_tenant(self, tenant_id: str) -> Iterator[DocumentRecord]:
        with self._lock:
            for d in self._by_id.values():
                if d.tenant_id == tenant_id:
                    yield d

    def global_stats(self) -> tuple[int, int]:
        """Return (total documents, distinct tenant count)."""
        with self._lock:
            tenants = {d.tenant_id for d in self._by_id.values()}
            return len(self._by_id), len(tenants)


_repository: DocumentRepository | None = None


def get_repository() -> DocumentRepository:
    global _repository
    if _repository is None:
        _repository = DocumentRepository()
    return _repository


def reset_repository_for_tests() -> None:
    global _repository
    _repository = DocumentRepository()
