"""/api/chat — front door for user queries.

`POST /api/chat`             — full Manager DAG, including Metodist's
                               Claude call on compliance queries.
`POST /api/chat/suggest`     — lighter Manager pass: skips Metodist and
                               uses a 2 s deadline per agent. Used by
                               the Recommendation panel for live
                               previews while the operator is typing.
`POST /api/chat/attachments` — multipart upload for letters / circulars
                               / business-spec drafts. Returns an
                               ``attachment_id`` the caller passes back
                               in ``ChatIn.attachment_id`` so Manager
                               folds the extracted text into the query.
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
    # When set, Manager loads the matching upload from app.attachments.store
    # and uses its OCR'd text as the primary retrieval/comparison context.
    # See app/api/routes_attachments.py for the upload endpoint.
    attachment_id: str | None = None


@router.post("/chat")
async def chat(body: ChatIn, user: AuthUser = Depends(current_user)) -> dict:
    return await manager.chat(
        query=body.message,
        user_id=user.id,
        role=user.role,
        attachment_id=body.attachment_id,
    )


@router.post("/chat/suggest")
async def chat_suggest(body: ChatIn, user: AuthUser = Depends(current_user)) -> dict:
    return await manager.suggest(
        query=body.message,
        user_id=user.id,
        role=user.role,
        attachment_id=body.attachment_id,
    )
