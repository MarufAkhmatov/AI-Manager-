"""/api/notifications — auto-audit findings feed for the TopHeader bell."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.agents.audit import audit_document
from app.deps import AuthUser, current_user, require_role
from app.notifications import store

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    limit: int = 50, user: AuthUser = Depends(current_user)
) -> dict:
    items = await store.list(limit=limit)
    unread = await store.unread_count()
    return {
        "unread": unread,
        "items": [n.to_dict() for n in items],
    }


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    notification_id: str, user: AuthUser = Depends(current_user)
) -> None:
    ok = await store.mark_read(notification_id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="unknown notification")
    return None


@router.post("/read-all")
async def mark_all_read(user: AuthUser = Depends(current_user)) -> dict:
    n = await store.mark_all_read()
    return {"marked": n}


class AuditIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=1, max_length=200_000)
    source_url: str | None = None


@router.post("/audit")
async def trigger_audit(
    body: AuditIn, user: AuthUser = Depends(require_role("admin"))
) -> dict:
    """Manually run a normative audit (admin only).

    Useful for testing the Phase-4 flow without waiting for the daily
    Regulyator crawl: paste an external act's title + text and get a
    finding in the bell. Same code path as the automatic trigger.
    """
    notif_id = await audit_document(
        title=body.title,
        text=body.text,
        source_url=body.source_url,
        role=user.role,
    )
    return {"notification_id": notif_id}
