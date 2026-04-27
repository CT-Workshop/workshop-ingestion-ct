from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DocumentVersion:
    version: int
    blob_key: str
    size_bytes: int
    content_type: str
    checksum_sha256: str
    metadata: dict[str, Any]
    created_at: datetime = field(default_factory=utcnow)
    created_by: str = ""


@dataclass
class DocumentRecord:
    """Logical document: versions belong to one tenant-owned aggregate."""

    id: UUID
    tenant_id: str
    logical_name: str
    versions: list[DocumentVersion] = field(default_factory=list)

    @property
    def latest(self) -> DocumentVersion | None:
        if not self.versions:
            return None
        return max(self.versions, key=lambda v: v.version)

    @classmethod
    def new(cls, tenant_id: str, logical_name: str) -> DocumentRecord:
        return cls(id=uuid4(), tenant_id=tenant_id, logical_name=logical_name)
