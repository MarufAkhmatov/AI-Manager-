"""FastAPI dependencies.

The real JWT-backed `current_user` ships in Phase 5. For Phase 3 a
permissive dev shim reads an optional `X-Dev-Role` header so the
chat path is exercisable end-to-end. The `require_role` helper is
already in its final shape — Phase 5 only swaps the user resolver.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status


@dataclass(slots=True)
class AuthUser:
    id: uuid.UUID | None
    username: str
    role: str  # 'admin' | 'analyst' | 'viewer'


async def current_user(x_dev_role: str | None = Header(default=None)) -> AuthUser:
    role = (x_dev_role or "analyst").lower()
    if role not in {"admin", "analyst", "viewer"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="unknown role")
    return AuthUser(id=None, username="dev", role=role)


def require_role(*allowed: str):
    async def _dep(user: AuthUser = Depends(current_user)) -> AuthUser:
        if user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="insufficient role")
        return user

    return _dep
