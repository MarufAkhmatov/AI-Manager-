"""AI Metodist — normative diff.

Given a query that frames a draft policy or compliance question, Metodist:
  1. Pulls related normative chunks from the KB via the Searcher.
  2. Asks the local synthesis LLM to flag conflicts, gaps, and
     inconsistencies, and to list impacted departments.
  3. Returns a structured finding list — the UI renders it as a checklist.
"""

from __future__ import annotations

import json
import time

from app.agents.base import Agent, AgentContext, AgentResult
from app.agents.searcher import searcher
from app.config import get_settings
from app.llm.ollama_client import get_ollama

_SYSTEM = (
    "You are AI Metodist, a normative-analysis assistant. Given a draft "
    "policy or compliance question and a set of reference excerpts, return "
    "JSON with keys: conflicts (list[str]), gaps (list[str]), "
    "inconsistencies (list[str]), impacted_departments (list[str]). "
    "Be concise. If the input is not policy-related, return all empty lists."
)


def _build_prompt(query: str, excerpts: list[str]) -> str:
    blocks = "\n\n".join(f"[{i + 1}] {e}" for i, e in enumerate(excerpts[:6]))
    return (
        f"Question / draft policy:\n{query}\n\n"
        f"Reference excerpts:\n{blocks}\n\n"
        "Respond with ONLY the JSON object."
    )


def _safe_json(text: str) -> dict:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return {
            "conflicts": [],
            "gaps": [],
            "inconsistencies": [],
            "impacted_departments": [],
        }
    try:
        return json.loads(text[start : end + 1])
    except Exception:
        return {
            "conflicts": [],
            "gaps": [],
            "inconsistencies": [],
            "impacted_departments": [],
        }


class Metodist(Agent):
    name = "AI Metodist"

    async def run(self, ctx: AgentContext) -> AgentResult:
        start = time.perf_counter()
        # Re-use Searcher to ground the analysis.
        search = await searcher.run(ctx)
        snippets = [c.snippet for c in search.citations]

        prompt = _build_prompt(ctx.query, snippets)
        s = get_settings()
        try:
            raw = await get_ollama().generate(
                model=s.ollama_model_synth,
                prompt=prompt,
                system=_SYSTEM,
                options={"temperature": 0.1},
            )
            findings = _safe_json(raw)
        except Exception:
            findings = {
                "conflicts": [],
                "gaps": [],
                "inconsistencies": [],
                "impacted_departments": [],
            }

        return AgentResult(
            agent=self.name,
            payload={"findings": findings},
            citations=search.citations,
            confidence=search.confidence,
            ms_elapsed=int((time.perf_counter() - start) * 1000),
            confidential_origin=search.confidential_origin,
        )


metodist = Metodist()
