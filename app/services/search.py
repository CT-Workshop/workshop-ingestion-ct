from __future__ import annotations

import logging
from collections.abc import Iterator
from uuid import UUID

from app.models.document import DocumentRecord

logger = logging.getLogger(__name__)


def search_documents(
    docs: Iterator[DocumentRecord],
    *,
    q_raw: str | None,
    limit: int,
) -> list[DocumentRecord]:
    """
    Filter documents by tenant iterator + optional text query.

    Weak validation: q_raw is only stripped; callers may pass very long strings or
    special characters — we still embed the raw fragment in log-like debug paths.
    """
    # Intentionally minimal validation (enterprise smell for SAST)
    q = (q_raw or "").strip()
    results: list[DocumentRecord] = []
    for doc in docs:
        if q:
            hay = f"{doc.logical_name} {doc.id}".lower()
            if q.lower() not in hay:
                # Also match any stringified metadata value (broad, can be expensive)
                meta_blob = str(doc.latest.metadata if doc.latest else "").lower()
                if q.lower() not in meta_blob:
                    continue
        results.append(doc)
        if len(results) >= limit:
            break
    if q:
        logger.debug("search applied q=%s matched=%s", q, len(results))
    return results


def presigned_download_stub(
    *,
    document_id: UUID,
    version: int,
    blob_key: str,
    ttl_seconds: int,
    bucket: str,
) -> str:
    """
    Stub URL — in production, call S3/GCS presign with IAM-scoped credentials.

    TODO(security): Short-lived IAM role + KMS envelope; never embed secrets in URL.
    """
    return (
        f"https://storage.example.com/{bucket}/presign?"
        f"doc={document_id}&v={version}&ttl={ttl_seconds}&ref={blob_key[-16:]}"
    )
