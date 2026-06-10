"""Stub agents used in demo / no-deps mode.

`AIM_DEMO=1` swaps the real Manager registry for these stubs so the
chat → recommendation flow is usable without Postgres + pgvector +
Redis + Ollama + the Anthropic API. The Secure egress + Shadow-guard
contracts are preserved — the Manager still funnels every demo result
through `app.agents.secure.Secure.run`.
"""

from __future__ import annotations

import asyncio
import time
from typing import ClassVar

from app.agents.base import Agent, AgentContext, AgentResult, Citation


class DemoSearcher(Agent):
    name: ClassVar[str] = "AI Searcher"

    async def run(self, ctx: AgentContext) -> AgentResult:
        start = time.perf_counter()
        await asyncio.sleep(0.05)  # tiny pause so the canvas pulse is visible
        q = ctx.query.strip() or "(empty query)"
        return AgentResult(
            agent=self.name,
            payload={
                "matches": [
                    {
                        "snippet": f"Demo: pgvector top-1 match for '{q[:120]}'",
                        "score": 0.87,
                        "title": "Demo Knowledge Base entry",
                    },
                    {
                        "snippet": "Demo: second-best match (kept for citation chip).",
                        "score": 0.74,
                        "title": "Demo policy fragment",
                    },
                ]
            },
            citations=[
                Citation(
                    document_id="demo-doc-1",
                    title="Demo Knowledge Base entry",
                    snippet=f"Demo retrieval snippet for: {q[:160]}",
                    score=0.87,
                ),
                Citation(
                    document_id="demo-doc-2",
                    title="Demo policy fragment",
                    snippet="This is a stub citation shown when running with AIM_DEMO=1.",
                    score=0.74,
                ),
            ],
            confidence=0.87,
            ms_elapsed=int((time.perf_counter() - start) * 1000),
            confidential_origin=False,
        )


class DemoMetodist(Agent):
    name: ClassVar[str] = "AI Metodist"

    async def run(self, ctx: AgentContext) -> AgentResult:
        start = time.perf_counter()
        # ~400 ms simulates the standalone's Claude round-trip without
        # actually calling Anthropic.
        await asyncio.sleep(0.4)
        q = ctx.query.strip() or "(empty query)"
        text = (
            "AI Metodist (demo) — bu javob soxta. Haqiqiy Claude chaqirig'i "
            "amalga oshirilmadi.\n\n"
            f"So'rov: \"{q[:200]}\"\n\n"
            "Demo holatda Metodist 2 ta ichki chunk va 1 ta tashqi normativ "
            "akt taqqoslagandek ko'rsatadi. AIM_DEMO=0 qilib backend'ni real "
            "stack bilan ko'tarsangiz — bu yerga aniq xulosa, conflict/gap/"
            "inconsistency ro'yxati keladi."
        )
        return AgentResult(
            agent=self.name,
            payload={
                "mode": "ask",
                "text": text,
                "internal_count": 2,
                "external_count": 2,
                # External chunks carry authority + source_url so the
                # CaseAnalysis builder can populate external_basis (and the
                # demo extraction can fabricate conflicts against them).
                "external_chunks": [
                    {
                        "source_url": "https://lex.uz/docs/demo-250",
                        "document_number": "ЎзР Қонуни 250-сон (demo)",
                        "authority": "lex.uz",
                        "text": "Demo: banklar faoliyati to'g'risidagi qonunning tegishli moddasi.",
                    },
                    {
                        "source_url": "https://cbu.uz/circulars/2025-14",
                        "document_number": "Циркуляр №2025/14 (demo)",
                        "authority": "cbu.uz",
                        "text": "Demo: kapital yetarliligi normativi to'g'risidagi sirkulyar bandi.",
                    },
                ],
            },
            citations=[
                Citation(
                    document_id="demo-internal-policy.pdf",
                    title="demo-internal-policy.pdf",
                    snippet="Demo internal chunk #1 — methodology rule excerpt.",
                    score=0.0,
                ),
                Citation(
                    document_id="https://lex.uz/demo",
                    title="ЎзР Қонуни (demo) · Lex.uz",
                    snippet="Demo external chunk — corresponding normative clause.",
                    score=0.0,
                ),
            ],
            confidence=0.6,
            ms_elapsed=int((time.perf_counter() - start) * 1000),
            confidential_origin=False,
        )


class DemoShadow(Agent):
    name: ClassVar[str] = "AI Shadow"

    async def run(self, ctx: AgentContext) -> AgentResult:
        start = time.perf_counter()
        await asyncio.sleep(0.08)
        # Viewers cannot see Lotus at all — preserve the contract even in demo.
        if ctx.role == "viewer":
            return AgentResult(
                agent=self.name,
                payload={"items": [], "denied": True},
                citations=[],
                confidence=0.0,
                ms_elapsed=int((time.perf_counter() - start) * 1000),
                confidential_origin=False,
            )
        return AgentResult(
            agent=self.name,
            payload={
                "items": [
                    {
                        "summary": "Demo Lotus summary — confidential origin. The Shadow-guard strips ids/titles/paths/source URLs from this payload before egress.",
                        "date": "2026-01-15",
                        "authority": "Internal",
                    }
                ]
            },
            # Lotus citations carry no document_id / title by design.
            citations=[
                Citation(
                    document_id=None,
                    title=None,
                    snippet="Demo Lotus summary excerpt.",
                    score=0.62,
                ),
            ],
            confidence=0.62,
            ms_elapsed=int((time.perf_counter() - start) * 1000),
            confidential_origin=True,
        )


def demo_registry() -> dict[str, Agent]:
    return {
        "AI Searcher": DemoSearcher(),
        "AI Metodist": DemoMetodist(),
        "AI Shadow": DemoShadow(),
    }
