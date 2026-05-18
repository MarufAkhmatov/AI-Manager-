"""/api/chat — front door for user queries."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.agents.manager import manager
from app.deps import current_user, AuthUser

router = APIRouter(prefix="/api", tags=["chat"])


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None


@router.post("/chat")
async def chat(body: ChatIn, user: AuthUser = Depends(current_user)) -> dict:
    return await manager.chat(query=body.message, user_id=user.id, role=user.role)
