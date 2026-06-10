"""Shadow-guard: strip metadata for confidential origins.

Applied at two layers:
1. AI Shadow agent strips fields from its own output (defence in depth).
2. AI Secure re-applies the rule to *any* agent result whose
   `confidential_origin` is True — so even if Searcher accidentally hands
   back a Lotus chunk it can't leak the doc id / title / path / source.
"""

from __future__ import annotations

from app.agents.base import AgentResult, Citation

FORBIDDEN_KEYS = ("document_id", "doc_id", "title", "source_url", "raw_path", "id")


def _scrub_dict(d: dict) -> dict:
    return {k: v for k, v in d.items() if k not in FORBIDDEN_KEYS}


def _scrub_citation(c: Citation) -> Citation:
    return Citation(document_id=None, title=None, snippet=c.snippet, score=c.score)


def scrub(result: AgentResult) -> AgentResult:
    if not result.confidential_origin:
        return result
    result.payload = _scrub_dict(result.payload)
    result.citations = [_scrub_citation(c) for c in result.citations]
    return result
