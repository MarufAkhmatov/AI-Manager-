"""FastAPI dependencies for auth + RBAC."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from app.security.jwt import decode_token


@dataclass(slots=True)
class AuthUser:
    id: uuid.UUID | None
    username: str
    role: str  # 'admin' | 'analyst' | 'viewer'


async def current_user(authorization: str | None = Header(default=None)) -> AuthUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_token(token)
    except Exception as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid token") from e

    role = payload.get("role", "viewer")
    if role not in {"admin", "analyst", "viewer"}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="unknown role")
    return AuthUser(
        id=uuid.UUID(payload["sub"]) if payload.get("sub") else None,
        username=payload.get("username", ""),
        role=role,
    )


def require_role(*allowed: str):
    async def _dep(user: AuthUser = Depends(current_user)) -> AuthUser:
        if user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="insufficient role")
        return user

    return _dep
