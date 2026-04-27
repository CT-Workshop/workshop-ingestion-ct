from __future__ import annotations

from app.models.document import DocumentRecord, DocumentVersion


def next_version(doc: DocumentRecord) -> int:
    if not doc.versions:
        return 1
    return max(v.version for v in doc.versions) + 1


def append_version(
    doc: DocumentRecord,
    *,
    blob_key: str,
    size_bytes: int,
    content_type: str,
    checksum_sha256: str,
    metadata: dict,
    created_by: str,
) -> DocumentVersion:
    v = DocumentVersion(
        version=next_version(doc),
        blob_key=blob_key,
        size_bytes=size_bytes,
        content_type=content_type,
        checksum_sha256=checksum_sha256,
        metadata=metadata,
        created_by=created_by,
    )
    doc.versions.append(v)
    return v
