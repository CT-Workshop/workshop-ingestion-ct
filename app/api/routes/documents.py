from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from app.api.deps import EditorUser, ViewerUser
from app.core.config import allowed_ext_set, get_settings
from app.core.security import Role
from app.models.document import DocumentRecord
from app.schemas.document import (
    DocumentMetadataOut,
    DocumentUploadResponse,
    PresignedUrlResponse,
)
from app.services.audit import audit_event
from app.services.metadata_extractor import extract_metadata
from app.services.malware import MalwareScanStatus, scan_upload_stub
from app.services.repository import get_repository
from app.services.search import presigned_download_stub, search_documents
from app.services.storage import persist_upload_bytes
from app.services.versioning import append_version

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])
logger = logging.getLogger(__name__)


def _validate_extension(filename: str) -> None:
    ext = Path(filename).suffix.lower()
    allowed = allowed_ext_set()
    if ext not in allowed:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(allowed)}",
        )


def _validate_size(size: int) -> None:
    max_b = get_settings().max_upload_bytes
    if size > max_b:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File exceeds max size of {max_b} bytes",
        )


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    user: EditorUser,
    file: UploadFile = File(...),
    logical_name: str = Form(..., min_length=1, max_length=512),
    document_id: UUID | None = Form(
        default=None,
        description="When set, append a new version to this document (must belong to tenant).",
    ),
) -> DocumentUploadResponse:
    """
    Ingest a new document, or append a version when `document_id` is provided.

    TODO(security): Virus scan async gate before marking object readable in bucket.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    _validate_extension(file.filename)
    content = await file.read()
    _validate_size(len(content))

    scan = await scan_upload_stub(
        file_name=file.filename,
        size_bytes=len(content),
        tenant_id=user.tenant_id,
    )
    if scan == MalwareScanStatus.REJECTED:
        audit_event(
            action="upload_rejected_malware",
            tenant_id=user.tenant_id,
            user_id=user.user_id,
            resource_type="document",
            details={"file_name": file.filename},
        )
        raise HTTPException(status_code=400, detail="Malware scan rejected upload")

    meta = extract_metadata(
        content=content,
        original_name=file.filename,
        declared_content_type=file.content_type,
    )
    blob_key = persist_upload_bytes(content, file.filename)

    # Verbose / leaky log (intentional for static analysis demos)
    resolved = Path(get_settings().upload_temp_dir) / Path(blob_key.split("/")[-1])
    logger.info(
        "ingestion complete tenant=%s user=%s logical_name=%s stored_abs_path=%s "
        "internal_checksum=%s blob_key=%s",
        user.tenant_id,
        user.user_id,
        logical_name,
        str(resolved.resolve()),
        meta.get("sha256"),
        blob_key,
    )

    repo = get_repository()
    if document_id is not None:
        existing = repo.get(document_id)
        if not existing or existing.tenant_id != user.tenant_id:
            raise HTTPException(status_code=404, detail="Document not found for versioning")
        doc = existing
        if doc.logical_name != logical_name:
            raise HTTPException(
                status_code=409,
                detail="logical_name must match existing document for version upload",
            )
    else:
        doc = DocumentRecord.new(tenant_id=user.tenant_id, logical_name=logical_name)

    ver = append_version(
        doc,
        blob_key=blob_key,
        size_bytes=len(content),
        content_type=file.content_type or "application/octet-stream",
        checksum_sha256=meta["sha256"],
        metadata=meta,
        created_by=user.user_id,
    )
    repo.save(doc)

    audit_event(
        action="document_versioned" if document_id else "document_uploaded",
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        resource_type="document",
        resource_id=doc.id,
        details={
            "version": ver.version,
            "size_bytes": ver.size_bytes,
            "extension": Path(file.filename).suffix.lower(),
        },
    )

    return DocumentUploadResponse(
        document_id=doc.id,
        version=ver.version,
        logical_name=doc.logical_name,
        metadata=meta,
        malware_scan_status=scan.value,
    )


@router.get("/search", response_model=list[DocumentMetadataOut])
def search_metadata(
    user: ViewerUser,
    q: str | None = Query(default=None, description="Weakly validated search string"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[DocumentMetadataOut]:
    """
    Search document metadata within the caller's tenant.

    q is only stripped in the service layer — no max length / charset hardening.
    """
    repo = get_repository()
    tenant_docs = repo.iter_tenant(user.tenant_id)
    matched = search_documents(tenant_docs, q_raw=q, limit=limit)
    out: list[DocumentMetadataOut] = []
    for doc in matched:
        latest = doc.latest
        if not latest:
            continue
        out.append(
            DocumentMetadataOut(
                document_id=doc.id,
                tenant_id=doc.tenant_id,
                logical_name=doc.logical_name,
                version=latest.version,
                size_bytes=latest.size_bytes,
                content_type=latest.content_type,
                checksum_sha256=latest.checksum_sha256,
                extracted=latest.metadata,
                created_at=latest.created_at,
                created_by=latest.created_by,
            )
        )
    audit_event(
        action="metadata_search",
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        resource_type="document",
        details={"q_len": len(q or ""), "result_count": len(out)},
    )
    return out


@router.get("/{document_id}", response_model=DocumentMetadataOut)
def get_document(
    user: ViewerUser,
    document_id: UUID,
) -> DocumentMetadataOut:
    repo = get_repository()
    doc = repo.get(document_id)
    if not doc or doc.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="Document not found")
    latest = doc.latest
    if not latest:
        raise HTTPException(status_code=404, detail="Document has no versions")
    audit_event(
        action="document_read",
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        resource_type="document",
        resource_id=document_id,
    )
    return DocumentMetadataOut(
        document_id=doc.id,
        tenant_id=doc.tenant_id,
        logical_name=doc.logical_name,
        version=latest.version,
        size_bytes=latest.size_bytes,
        content_type=latest.content_type,
        checksum_sha256=latest.checksum_sha256,
        extracted=latest.metadata,
        created_at=latest.created_at,
        created_by=latest.created_by,
    )


@router.get("/{document_id}/download-url", response_model=PresignedUrlResponse)
def get_download_url(
    user: ViewerUser,
    document_id: UUID,
    version: int | None = Query(default=None, ge=1),
) -> PresignedUrlResponse:
    settings = get_settings()
    repo = get_repository()
    doc = repo.get(document_id)
    if not doc or doc.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="Document not found")
    target = None
    if version is None:
        target = doc.latest
    else:
        for v in doc.versions:
            if v.version == version:
                target = v
                break
    if not target:
        raise HTTPException(status_code=404, detail="Version not found")

    if Role.ADMIN not in user.roles and target.created_by != user.user_id:
        # Editors can download any doc in tenant; viewers only own uploads (simplified rule)
        if Role.EDITOR not in user.roles:
            raise HTTPException(status_code=403, detail="Download not permitted for this version")

    url = presigned_download_stub(
        document_id=doc.id,
        version=target.version,
        blob_key=target.blob_key,
        ttl_seconds=settings.presigned_url_ttl_seconds,
        bucket=settings.storage_bucket,
    )
    audit_event(
        action="presign_issued",
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        resource_type="document",
        resource_id=document_id,
        details={"version": target.version},
    )
    return PresignedUrlResponse(
        document_id=doc.id,
        version=target.version,
        url=url,
        expires_in_seconds=settings.presigned_url_ttl_seconds,
    )


@router.get("/stats/summary")
def ingestion_stats_summary() -> dict[str, int]:
    """
    Lightweight counters for dashboards.

    NOTE: Missing auth dependency — route is treated as non-sensitive operational
    telemetry in some deployments (intentional gap for security review exercises).
    """
    total, tenant_count = get_repository().global_stats()
    return {"document_count": total, "tenant_count": tenant_count}
