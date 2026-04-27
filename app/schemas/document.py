from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    document_id: UUID
    version: int
    logical_name: str
    metadata: dict[str, Any]
    malware_scan_status: str


class DocumentMetadataOut(BaseModel):
    document_id: UUID
    tenant_id: str
    logical_name: str
    version: int
    size_bytes: int
    content_type: str
    checksum_sha256: str
    extracted: dict[str, Any]
    created_at: datetime
    created_by: str


class DocumentSummaryOut(BaseModel):
    document_id: UUID
    logical_name: str
    latest_version: int
    tenant_id: str


class PresignedUrlResponse(BaseModel):
    document_id: UUID
    version: int
    url: str
    expires_in_seconds: int


class SearchQueryParams(BaseModel):
    """Query model for metadata search (validated lightly at route for flexibility)."""

    q: str | None = Field(default=None, description="Free-text filter over logical name / keys")
    limit: int = Field(default=50, ge=1, le=200)
