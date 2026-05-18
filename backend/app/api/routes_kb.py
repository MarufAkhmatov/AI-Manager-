"""/api/kb — knowledge base stats, listing, upload, reindex."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select

from app.agents.architect import architect
from app.config import get_settings
from app.db.models import Document
from app.db.session import session_scope
from app.deps import AuthUser, current_user, require_role
from app.security.paths import safe_join

router = APIRouter(prefix="/api/kb", tags=["kb"])


@router.get("/stats")
async def stats(user: AuthUser = Depends(current_user)) -> dict:
    async with session_scope() as session:
        total = await session.scalar(select(func.count(Document.id)))
        by_cat = (
            await session.execute(
                select(Document.category, func.count(Document.id)).group_by(Document.category)
            )
        ).all()
    return {
        "total": int(total or 0),
        "by_category": {c: int(n) for c, n in by_cat},
    }


@router.get("/documents")
async def list_documents(
    category: str | None = None,
    user: AuthUser = Depends(current_user),
) -> list[dict]:
    """List non-confidential documents.

    Confidential docs are still returned but with id/title/path/source
    blanked out so the UI can render them as `—`. Viewers don't see
    Lotus rows at all.
    """
    async with session_scope() as session:
        stmt = select(Document).where(Document.status == "active")
        if category:
            stmt = stmt.where(Document.category == category)
        rows = (await session.execute(stmt)).scalars().all()

    out: list[dict] = []
    for r in rows:
        if r.is_confidential and user.role == "viewer":
            continue
        if r.is_confidential:
            out.append(
                {
                    "id": None,
                    "title": None,
                    "category": r.category,
                    "authority": r.authority,
                    "status": r.status,
                    "issued_at": r.issued_at.isoformat() if r.issued_at else None,
                    "is_confidential": True,
                }
            )
        else:
            out.append(
                {
                    "id": str(r.id),
                    "title": r.title,
                    "category": r.category,
                    "authority": r.authority,
                    "status": r.status,
                    "issued_at": r.issued_at.isoformat() if r.issued_at else None,
                    "is_confidential": False,
                }
            )
    return out


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload(
    file: UploadFile = File(...),
    user: AuthUser = Depends(require_role("admin")),
) -> dict:
    s = get_settings()
    raw_dir = safe_join(s.kb_raw, "_uploads")
    raw_dir.mkdir(parents=True, exist_ok=True)
    if not file.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="filename required")
    dest = safe_join(raw_dir, file.filename)
    dest.write_bytes(await file.read())
    # The watcher will pick this up and run the pipeline.
    return {"stored_at": str(dest)}


@router.post("/reindex")
async def reindex(user: AuthUser = Depends(require_role("admin"))) -> dict:
    count = await architect.reindex()
    return {"processed": count}
