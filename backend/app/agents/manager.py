"""AI Manager — orchestrator.

Flow per request:
  1. Intent detection (rule-based; LLM fallback hook reserved).
  2. Plan: select sub-agents based on intent.
  3. Parallel dispatch with a per-agent 2.2s soft deadline
     (slow agents return partials).
  4. Aggregate into one AgentResult.
  5. **Mandatory** pass through AI Secure (egress sanitizer).
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import replace
from typing import Iterable

from app.agents.base import Agent, AgentContext, AgentResult, Citation
from app.agents.searcher import searcher
from app.agents.secure import secure
from app.events import emit

AGENT_DEADLINE_S = 2.2


def _detect_intent(q: str) -> set[str]:
    """Return the set of agent names to run, based on simple keyword rules.

    The Searcher is always part of the plan because every chat answer
    benefits from grounded citations; AI Secure is appended unconditionally
    at the egress stage.
    """
    lower = q.lower()
    plan: set[str] = {"AI Searcher"}

    if any(k in lower for k in ("lotus", "internal", "confidential", "внутр", "лотус")):
        plan.add("AI Shadow")
    if any(
        k in lower
        for k in (
            "compliant",
            "conflict",
            "gap",
            "policy",
            "normative",
            "соответств",
            "конфликт",
            "нарушени",
        )
    ):
        plan.add("AI Metodist")
    if any(k in lower for k in ("cbu", "lex.uz", "ipakyuli", "regulator", "circular", "регулят")):
        # Regulyator data is in KB already; the *agent* itself doesn't run
        # on the request path. Mark intent for observability only.
        pass
    return plan


def _registry() -> dict[str, Agent]:
    # Lazy import to keep the optional Phase 4 agents out of Phase 3 dep graph.
    reg: dict[str, Agent] = {"AI Searcher": searcher}
    try:
        from app.agents.metodist import metodist

        reg["AI Metodist"] = metodist
    except Exception:
        pass
    try:
        from app.agents.shadow import shadow

        reg["AI Shadow"] = shadow
    except Exception:
        pass
    return reg


async def _run_with_deadline(agent: Agent, ctx: AgentContext) -> AgentResult | None:
    try:
        return await asyncio.wait_for(agent.run(ctx), timeout=AGENT_DEADLINE_S)
    except asyncio.TimeoutError:
        await emit(agent.name, "timeout", task_id=str(ctx.task_id))
        return None
    except Exception as e:
        await emit(
            agent.name, "error", task_id=str(ctx.task_id), error=f"{type(e).__name__}: {e}"
        )
        return None


def _aggregate(name: str, parts: Iterable[AgentResult]) -> AgentResult:
    citations: list[Citation] = []
    payload: dict = {"agents": {}}
    confidential = False
    for p in parts:
        payload["agents"][p.agent] = p.payload
        citations.extend(p.citations)
        if p.confidential_origin:
            confidential = True
    return AgentResult(
        agent=name,
        payload=payload,
        citations=citations,
        confidence=max((p.confidence for p in parts), default=0.0),
        confidential_origin=confidential,
    )


class Manager:
    name = "AI Manager"

    async def chat(
        self,
        *,
        query: str,
        user_id: uuid.UUID | None,
        role: str,
    ) -> dict:
        task_id = uuid.uuid4()
        ctx = AgentContext(task_id=task_id, user_id=user_id, role=role, query=query)
        start = time.perf_counter()

        plan = _detect_intent(query)
        await emit(
            self.name, "plan", task_id=str(task_id), agents=sorted(plan), query=query[:200]
        )

        reg = _registry()
        runnable = [reg[a] for a in plan if a in reg]
        results = await asyncio.gather(*[_run_with_deadline(a, ctx) for a in runnable])
        parts = [r for r in results if r is not None]

        aggregate = _aggregate(self.name, parts)
        ctx.scratch["aggregate"] = aggregate

        final = await secure.run(ctx)
        ms = int((time.perf_counter() - start) * 1000)
        await emit(self.name, "done", task_id=str(task_id), ms_total=ms)

        return {
            "task_id": str(task_id),
            "agents_used": [p.agent for p in parts] + [secure.name],
            "response": final.payload,
            "citations": [c.__dict__ for c in final.citations],
            "ms_total": ms,
        }


manager = Manager()
