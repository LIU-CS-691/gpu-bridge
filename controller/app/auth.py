from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from . import crud
from .config import settings
from .db import get_db


def _resolve_key(
    x_api_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if not x_api_token:
        raise HTTPException(status_code=401, detail="Missing X-API-Token header")

    if x_api_token == settings.bootstrap_token:
        return "admin"

    api_key = crud.get_api_key_by_key(db, x_api_token)
    if not api_key or not api_key.is_active:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    return api_key.role


def require_role(*allowed_roles: str):
    def dependency(role: str = Depends(_resolve_key)):
        if role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Requires role: {', '.join(allowed_roles)}",
            )
        return role

    return dependency
