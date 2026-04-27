from typing import Annotated

from fastapi import Depends

from app.core.security import (
    Principal,
    parse_gateway_principal,
    require_editor_or_admin,
    require_viewer_or_above,
)


CurrentUser = Annotated[Principal, Depends(parse_gateway_principal)]


def editor_principal(user: Principal = Depends(parse_gateway_principal)) -> Principal:
    require_editor_or_admin(user)
    return user


def viewer_principal(user: Principal = Depends(parse_gateway_principal)) -> Principal:
    require_viewer_or_above(user)
    return user


EditorUser = Annotated[Principal, Depends(editor_principal)]
ViewerUser = Annotated[Principal, Depends(viewer_principal)]
