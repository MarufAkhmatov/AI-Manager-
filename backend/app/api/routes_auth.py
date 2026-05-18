"""/api/auth — login / logout / me."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

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
