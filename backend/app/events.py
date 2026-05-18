"""In-process event bus for activity events.

The WS hub (Phase 3) subscribes to this bus and fans events out to
connected clients. Keeping it in-process avoids a hard Redis dependency
on the hot path for the Activity Panel.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

_QUEUE_MAXSIZE = 1024


@dataclass(slots=True)
class Event:
    agent: str
    event: str
    payload: dict[str, Any] = field(default_factory=dict)
    task_id: str | None = None
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_json(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "agent": self.agent,
            "event": self.event,
            "task_id": self.task_id,
            "payload": self.payload,
        }


class EventBus:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[Event]] = set()

    async def publish(self, event: Event) -> None:
        dead: list[asyncio.Queue[Event]] = []
        for q in self._subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(q)  # drop slow subscribers
        for q in dead:
            self._subscribers.discard(q)

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[asyncio.Queue[Event]]:
        q: asyncio.Queue[Event] = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
        self._subscribers.add(q)
        try:
            yield q
        finally:
            self._subscribers.discard(q)


bus = EventBus()


async def emit(agent: str, event: str, **payload: Any) -> None:
    task_id = payload.pop("task_id", None)
    await bus.publish(Event(agent=agent, event=event, payload=payload, task_id=task_id))
