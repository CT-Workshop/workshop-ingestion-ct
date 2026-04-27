"""
Authorization helpers.

TODO(security): Verify JWT signatures against JWKS from jwt_issuer instead of
trusting gateway-injected headers in production edge paths.
TODO(security): Add mTLS between ingress and this service for internal APIs.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Iterable

from fastapi import Header, HTTPException, status


@dataclass(frozen=True)
class Principal:
    """Represents an authenticated caller (typically derived from JWT claims)."""

    user_id: str
    tenant_id: str
    roles: frozenset[str]


class Role:
    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"


def _decode_b64url_json(segment: str) -> dict:
    padding = "=" * (-len(segment) % 4)
    raw = base64.urlsafe_b64decode(segment + padding)
    return json.loads(raw.decode("utf-8"))


def parse_gateway_principal(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_roles: str | None = Header(default=None, alias="X-User-Roles"),
) -> Principal:
    """
    Parse principal from Authorization (Bearer JWT payload) with header fallbacks.

    In production, the API gateway validates the JWT; this service re-parses claims
    for RBAC. Demo mode: if Bearer present, decode payload without signature verify.
    """
    roles: set[str] = set()
    user_id = x_user_id or ""
    tenant_id = x_tenant_id or ""

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        try:
            parts = token.split(".")
            if len(parts) >= 2:
                claims = _decode_b64url_json(parts[1])
                user_id = str(claims.get("sub", user_id))
                tenant_id = str(claims.get("tenant_id", tenant_id))
                r = claims.get("roles")
                if isinstance(r, list):
                    roles = {str(x) for x in r}
                elif isinstance(r, str):
                    roles = {r}
        except (ValueError, json.JSONDecodeError, KeyError):
            pass

    if x_user_roles:
        roles |= {r.strip() for r in x_user_roles.split(",") if r.strip()}

    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing identity context (user_id / tenant_id)",
        )

    return Principal(
        user_id=user_id,
        tenant_id=tenant_id,
        roles=frozenset({r.lower() for r in roles}),
    )


def require_roles(principal: Principal, allowed: Iterable[str]) -> None:
    allowed_l = {a.lower() for a in allowed}
    if not principal.roles & allowed_l:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role for this operation",
        )


def require_editor_or_admin(principal: Principal) -> None:
    require_roles(principal, (Role.EDITOR, Role.ADMIN))


def require_viewer_or_above(principal: Principal) -> None:
    require_roles(principal, (Role.VIEWER, Role.EDITOR, Role.ADMIN))
