"""AI Secure — mandatory final egress sanitizer.

Every agent result that leaves the API passes through Secure. It applies
PII masking and the Shadow-guard rule (strip metadata from confidential
origins). It is the last node of the Manager DAG by construction; if
Secure was bypassed the Manager refuses to return a response.
"""

from __future__ import annotations

import time

from app.agents.base import Agent, AgentContext, AgentResult, Citation
from app.security.masking import mask_text
from app.security.shadow_guard import scrub


def _mask_citation(c: Citation) -> Citation:
    return Citation(
        document_id=c.document_id,
        title=mask_text(c.title) if c.title else None,
        snippet=mask_text(c.snippet),
        score=c.score,
    )


def _mask_payload(p: dict) -> dict:
    out: dict = {}
    for k, v in p.items():
        if isinstance(v, str):
            out[k] = mask_text(v)
        elif isinstance(v, list):
            out[k] = [_mask_payload(i) if isinstance(i, dict) else (mask_text(i) if isinstance(i, str) else i) for i in v]
        elif isinstance(v, dict):
            out[k] = _mask_payload(v)
        else:
            out[k] = v
    return out


class Secure(Agent):
    name = "AI Secure"

    async def run(self, ctx: AgentContext) -> AgentResult:
        # Secure is invoked directly by the Manager with a pre-aggregated
        # payload in ctx.scratch["aggregate"]. It returns the masked
        # AgentResult ready to ship.
        start = time.perf_counter()
        agg: AgentResult = ctx.scratch["aggregate"]
        agg = scrub(agg)
        agg.payload = _mask_payload(agg.payload)
        agg.citations = [_mask_citation(c) for c in agg.citations]
        agg.ms_elapsed = int((time.perf_counter() - start) * 1000)
        agg.agent = self.name
        return agg


secure = Secure()
