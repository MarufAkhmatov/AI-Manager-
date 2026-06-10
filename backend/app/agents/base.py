"""Shared agent contracts.

Every agent implements the same `run(ctx) -> AgentResult` shape so the
Manager can dispatch them uniformly via `asyncio.gather` with deadlines.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class AgentContext:
    task_id: uuid.UUID
    user_id: uuid.UUID | None
    role: str
    query: str
    scratch: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Citation:
    document_id: str | None
    title: str | None
    snippet: str
    score: float


@dataclass(slots=True)
class AgentResult:
    agent: str
    payload: dict[str, Any]
    citations: list[Citation] = field(default_factory=list)
    confidence: float = 0.0
    ms_elapsed: int = 0
    confidential_origin: bool = False  # set True if any source was Lotus


class Agent(Protocol):
    name: str

    async def run(self, ctx: AgentContext) -> AgentResult: ...
