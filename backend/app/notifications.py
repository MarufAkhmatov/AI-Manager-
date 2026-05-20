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
        return n

    async def list(self, limit: int = 50) -> list[Notification]:
        async with self._lock:
            return list(self._items)[:limit]

    async def unread_count(self) -> int:
        async with self._lock:
            return sum(1 for n in self._items if not n.read)

    async def mark_read(self, notification_id: str) -> bool:
        async with self._lock:
            for n in self._items:
                if n.id == notification_id:
                    n.read = True
                    return True
            return False

    async def mark_all_read(self) -> int:
        async with self._lock:
            count = 0
            for n in self._items:
                if not n.read:
                    n.read = True
                    count += 1
            return count


store = _Store()


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
