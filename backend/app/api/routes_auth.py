"""/api/auth — login / logout / me."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.config import get_settings
from app.db.models import User
from app.db.session import session_scope
from app.deps import AuthUser, current_user
from app.security.audit import record as audit
from app.security.jwt import issue_token
from app.security.passwords import verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/login", response_model=LoginOut)
async def login(body: LoginIn) -> LoginOut:
    settings = get_settings()

    # Demo mode: no database, no password store. The only working account
    # is `admin` (any non-empty password). This branch never touches
    # session_scope, so it works without Postgres.
    if settings.aim_demo:
        if body.username != "admin":
            await audit(
                "auth.login.failed",
                username=body.username,
                reason="demo_only_admin",
            )
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                detail="demo mode accepts only username 'admin' (any password)",
            )
        demo_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        await audit(
            "auth.login.ok",
            user_id=str(demo_id),
            username="admin",
            role="admin",
            demo=True,
        )
        token = issue_token(user_id=demo_id, username="admin", role="admin")
        return LoginOut(
            access_token=token,
            user={"id": str(demo_id), "username": "admin", "role": "admin"},
        )

    async with session_scope() as session:
        user = await session.scalar(select(User).where(User.username == body.username))
    if user is None or user.disabled_at is not None:
        await audit("auth.login.failed", username=body.username, reason="unknown_or_disabled")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    if not verify_password(body.password, user.password_hash):
        await audit("auth.login.failed", username=body.username, reason="bad_password")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")

    await audit("auth.login.ok", user_id=str(user.id), username=user.username, role=user.role)
    token = issue_token(user_id=user.id, username=user.username, role=user.role)
    return LoginOut(
        access_token=token,
        user={"id": str(user.id), "username": user.username, "role": user.role},
    )


@router.get("/me")
async def me(user: AuthUser = Depends(current_user)) -> dict:
    return {"id": str(user.id) if user.id else None, "username": user.username, "role": user.role}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout() -> None:
    # JWT is stateless; logout is a client-side discard. We could add a
    # token revocation list later if needed.
    return None
