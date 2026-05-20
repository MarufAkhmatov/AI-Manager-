"""In-memory notification store.

Phase 4 surfaces auto-audit findings: when AI Regulyator pulls in a new
external act and AI Architect finishes ingesting it, the platform runs a
normative audit (new act vs internal KB) and drops the result here. The
TopHeader bell reads the unread count; the dropdown lists recent findings;
clicking one loads its CaseAnalysis into the Recommendation panel.

Kept in process memory (bounded, newest-first) rather than the DB so it
works identically in demo mode and the real stack without a migration.
Notifications don't survive a restart — that's fine for an operator-facing
"what changed today" feed; the durable record is the agent_logs / audit
chain.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from typing import Any

from app.config import get_settings

MAX_ENTRIES = 200


@dataclass(slots=True)
class Notification:
    id: str
    kind: str                       # "audit" for now
    title: str
    source_url: str | None
    summary: str
    case_analysis: dict[str, Any]
    created_at: float = field(default_factory=time.time)
    read: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


class _Store:
    def __init__(self) -> None:
        self._items: deque[Notification] = deque(maxlen=MAX_ENTRIES)
        self._lock = asyncio.Lock()

    async def add(self, n: Notification) -> Notification:
        async with self._lock:
            self._items.appendleft(n)
        await _persist_add(n)
        return n

    async def list(self, limit: int = 50) -> list[Notification]:
        async with self._lock:
            return list(self._items)[:limit]

    async def unread_count(self) -> int:
        async with self._lock:
            return sum(1 for n in self._items if not n.read)

    async def mark_read(self, notification_id: str) -> bool:
        async with self._lock:
            found = False
            for n in self._items:
                if n.id == notification_id:
                    n.read = True
                    found = True
                    break
        if found:
            await _persist_read([notification_id])
        return found

    async def mark_all_read(self) -> int:
        async with self._lock:
            ids = [n.id for n in self._items if not n.read]
            for n in self._items:
                n.read = True
        if ids:
            await _persist_read(ids)
        return len(ids)

    async def hydrate(self, items: list[Notification]) -> None:
        """Replace the in-memory contents with rows loaded from the DB.
        Called once at startup (newest-first)."""
        async with self._lock:
            self._items.clear()
            for n in items:  # items already newest-first
                self._items.append(n)


store = _Store()


# ─── Best-effort DB persistence ──────────────────────────────────────────
#
# The in-memory store is the hot path; the `notifications` table is the
# durable backing so findings survive a restart. Every DB op is wrapped so
# a missing table (demo mode / un-migrated dev DB) degrades to memory-only
# without breaking the request.


async def _persist_add(n: Notification) -> None:
    if get_settings().aim_demo:
        return
    try:
        import uuid as _uuid

        from app.db.models import Notification as NotifRow
        from app.db.session import session_scope

        async with session_scope() as session:
            session.add(
                NotifRow(
                    id=_uuid.UUID(n.id),
                    kind=n.kind,
                    title=n.title,
                    source_url=n.source_url,
                    summary=n.summary,
                    case_analysis=n.case_analysis,
                    read=n.read,
                )
            )
    except Exception:
        # Missing table / DB down — memory-only fallback.
        return


async def _persist_read(ids: list[str]) -> None:
    if get_settings().aim_demo:
        return
    try:
        import uuid as _uuid

        from sqlalchemy import update

        from app.db.models import Notification as NotifRow
        from app.db.session import session_scope

        uuids = []
        for i in ids:
            try:
                uuids.append(_uuid.UUID(i))
            except ValueError:
                continue
        if not uuids:
            return
        async with session_scope() as session:
            await session.execute(
                update(NotifRow).where(NotifRow.id.in_(uuids)).values(read=True)
            )
    except Exception:
        return


async def load_from_db(limit: int = MAX_ENTRIES) -> int:
    """Hydrate the in-memory store from the DB at startup. Best-effort:
    returns the number of rows loaded (0 in demo mode / on any error)."""
    if get_settings().aim_demo:
        return 0
    try:
        from sqlalchemy import desc, select

        from app.db.models import Notification as NotifRow
        from app.db.session import session_scope

        async with session_scope() as session:
            rows = (
                await session.execute(
                    select(NotifRow).order_by(desc(NotifRow.created_at)).limit(limit)
                )
            ).scalars().all()
        items = [
            Notification(
                id=str(r.id),
                kind=r.kind,
                title=r.title,
                source_url=r.source_url,
                summary=r.summary,
                case_analysis=r.case_analysis or {},
                created_at=r.created_at.timestamp() if r.created_at else time.time(),
                read=r.read,
            )
            for r in rows
        ]
        await store.hydrate(items)
        return len(items)
    except Exception:
        return 0


def new_notification(
    *,
    kind: str,
    title: str,
    source_url: str | None,
    summary: str,
    case_analysis: dict[str, Any],
) -> Notification:
    return Notification(
        id=uuid.uuid4().hex,
        kind=kind,
        title=title,
        source_url=source_url,
        summary=summary,
        case_analysis=case_analysis,
    )
