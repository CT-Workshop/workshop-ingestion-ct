from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def audit_event(
    *,
    action: str,
    tenant_id: str,
    user_id: str,
    resource_type: str,
    resource_id: UUID | str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """
    Structured audit line suitable for shipping to SIEM.

    Avoid logging raw file contents or secrets.
    """
    payload = {
        "ts": utcnow().isoformat(),
        "action": action,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "resource_type": resource_type,
        "resource_id": str(resource_id) if resource_id is not None else None,
        "details": details or {},
    }
    logger.info("AUDIT %s", payload)
