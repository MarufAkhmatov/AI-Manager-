"""/api/chat — front door for user queries.

`POST /api/chat`         — full Manager DAG, including Metodist's Claude call
                           on compliance queries. Up to ~15 s on cold paths.
`POST /api/chat/suggest` — lighter preview Manager: skips heavy agents
                           (Metodist) and uses a tight 2 s deadline per
                           agent. Designed for live-as-you-type previews
                           from the Recommendation panel; cached Searcher
                           hits usually return in well under 200 ms.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.agents.manager import manager
from app.deps import AuthUser, current_user

router = APIRouter(prefix="/api", tags=["chat"])


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None


@router.post("/chat")
async def chat(body: ChatIn, user: AuthUser = Depends(current_user)) -> dict:
    return await manager.chat(query=body.message, user_id=user.id, role=user.role)


@router.post("/chat/suggest")
async def chat_suggest(body: ChatIn, user: AuthUser = Depends(current_user)) -> dict:
    return await manager.suggest(query=body.message, user_id=user.id, role=user.role)
