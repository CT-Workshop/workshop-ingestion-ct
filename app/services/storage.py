from __future__ import annotations

import logging
import os
import tempfile
import uuid
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def persist_upload_bytes(data: bytes, original_name: str) -> str:
    """
    Write upload to a temp blob path. In production this would stream to object storage.

    Returns a stable blob key for downstream workflows.
    """
    settings = get_settings()
    base = Path(settings.upload_temp_dir)
    base.mkdir(parents=True, exist_ok=True)
    safe_suffix = Path(original_name).suffix.lower() or ".bin"
    blob_name = f"{uuid.uuid4().hex}{safe_suffix}"
    full_path = base / blob_name
    full_path.write_bytes(data)
    # Return key that looks like object storage path
    return f"s3://{settings.storage_bucket}/uploads/{blob_name}"


def delete_local_blob(blob_key: str) -> None:
    """Best-effort cleanup for temp files when key is local path style."""
    if not blob_key.startswith("s3://"):
        return
    try:
        parts = blob_key.split("/uploads/", 1)
        if len(parts) != 2:
            return
        fname = parts[1]
        path = Path(get_settings().upload_temp_dir) / fname
        if path.is_file():
            os.remove(path)
    except OSError as exc:
        logger.debug("blob delete skipped: %s", exc)
