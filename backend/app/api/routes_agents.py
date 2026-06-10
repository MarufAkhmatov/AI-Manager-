"""/api/agents — introspection + admin-only direct invoke."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import desc, select

from app.agents.base import AgentContext
from app.agents.manager import manager
from app.agents.metodist import metodist
from app.agents.regulyator import regulyator
from app.agents.searcher import searcher
from app.agents.secure import secure
from app.agents.shadow import shadow
from app.db.models import AgentLog
from app.db.session import session_scope
from app.deps import AuthUser, current_user, require_role

router = APIRouter(prefix="/api/agents", tags=["agents"])

_REGISTRY = {
    "AI Manager": manager,
    "AI Architect": None,  # background-only
    "AI Searcher": searcher,
    "AI Metodist": metodist,
    "AI Shadow": shadow,
    "AI Secure": secure,
    "AI Regulyator": regulyator,
}


class InvokeIn(BaseModel):
    query: str


@router.get("")
async def list_agents(user: AuthUser = Depends(current_user)) -> list[dict]:
    return [{"name": n, "active": v is not None} for n, v in _REGISTRY.items()]


@router.get("/{name}/logs")
async def agent_logs(name: str, limit: int = 50, user: AuthUser = Depends(current_user)) -> list[dict]:
    if name not in _REGISTRY:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="unknown agent")
    async with session_scope() as session:
        rows = (
            await session.execute(
                select(AgentLog)
                .where(AgentLog.agent == name)
                .order_by(desc(AgentLog.created_at))
                .limit(limit)
            )
        ).scalars().all()
    return [
        {
            "id": r.id,
            "task_id": str(r.task_id) if r.task_id else None,
            "event": r.event,
            "payload": r.payload,
            "ms_elapsed": r.ms_elapsed,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.post("/{name}/invoke")
async def invoke(
    name: str,
    body: InvokeIn,
    user: AuthUser = Depends(require_role("admin")),
) -> dict:
    agent = _REGISTRY.get(name)
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="agent not directly invokable")
    if name == "AI Manager":
        return await manager.chat(query=body.query, user_id=user.id, role=user.role)
    if name == "AI Regulyator":
        return {"crawl": await regulyator.crawl_once()}

    ctx = AgentContext(
        task_id=uuid.uuid4(), user_id=user.id, role=user.role, query=body.query
    )
    result = await agent.run(ctx)
    return {"agent": result.agent, "payload": result.payload, "ms": result.ms_elapsed}
