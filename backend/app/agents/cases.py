"""Structured case-analysis output.

The platform's three flagship use cases all produce the same shape:

  * a short summary,
  * a list of internal documents impacted (with clause / department),
  * a list of external acts that drove the analysis (with sources),
  * a list of conflicts (internal vs external),
  * a list of concrete recommendations / suggested amendments.

`CaseAnalysis` is the canonical schema. The Manager builds one from the
aggregate it gets back from Searcher / Metodist / Shadow and ships it
alongside the existing free-form `response` blob so the frontend's
Recommendation panel can render structured sections (collapsible by
intent) without losing the raw agent payload for power users.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

from app.agents.base import AgentResult, Citation


# ─── Schema ─────────────────────────────────────────────────────────────


@dataclass(slots=True)
class InternalImpact:
    """An internal KB document that the analysis touches."""

    document_id: str | None       # None for Lotus origin (shadow-guard)
    title: str | None             # ditto
    snippet: str
    score: float                  # cosine-similarity for retrieval-based hits
    section: str | None = None    # extracted section / clause path if known
    department: str | None = None # inferred bank department from path


@dataclass(slots=True)
class ExternalBasis:
    """An external normative act (lex.uz / cbu.uz / ipakyulibank.uz)."""

    authority: str | None         # "cbu.uz", "lex.uz", "ipakyulibank.uz"
    source_url: str | None        # canonical URL on the regulator site
    title: str | None             # document number or page title
    snippet: str


@dataclass(slots=True)
class Conflict:
    """A specific clash between an internal clause and an external act."""

    internal_ref: str             # human-readable "doc.title · section"
    external_ref: str             # human-readable "authority · doc number"
    why: str                      # free-text explanation


@dataclass(slots=True)
class Recommendation:
    """A concrete action the analyst should take."""

    action: str                   # e.g. "amend", "draft", "withdraw"
    target_doc: str | None        # internal doc to change
    target_clause: str | None     # specific clause / section
    suggested_text: str           # plain-text proposed wording / direction


@dataclass(slots=True)
class CaseAnalysis:
    """End-user-facing structured response. Always JSON-serialisable."""

    summary: str = ""
    affected_internal: list[InternalImpact] = field(default_factory=list)
    external_basis: list[ExternalBasis] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)
    affected_departments: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ─── Department inference ───────────────────────────────────────────────

# Bank-department mapping derived from KB path segments. The KB tree is
# typically organised under KB\<bucket>\<department>\…; we surface the
# department name so the analyst can route the impact to the right team
# without manually opening every citation.
_DEPT_HINTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)\b(credit|kredit|qarz)\b"),       "Credit"),
    (re.compile(r"(?i)\b(risk|risk)\b"),                 "Risk"),
    (re.compile(r"(?i)\b(compliance|complayens|aml|kyc)\b"), "Compliance"),
    (re.compile(r"(?i)\b(treasury|kazna)\b"),            "Treasury"),
    (re.compile(r"(?i)\b(operations|operatsiya)\b"),     "Operations"),
    (re.compile(r"(?i)\b(it|tex|texnologi|cyber)\b"),    "IT"),
    (re.compile(r"(?i)\b(hr|kadr)\b"),                   "HR"),
    (re.compile(r"(?i)\b(legal|yuridik|huquq)\b"),       "Legal"),
    (re.compile(r"(?i)\b(retail|chakana)\b"),            "Retail"),
    (re.compile(r"(?i)\b(corporate|korporativ)\b"),      "Corporate"),
)


def _infer_department(path_or_title: str | None) -> str | None:
    if not path_or_title:
        return None
    # Walk individual path segments AND the raw string — file-system layout
    # carries department info, but so do document titles.
    candidates: list[str] = [path_or_title]
    for sep in ("\\", "/"):
        candidates.extend(p for p in path_or_title.split(sep) if p)
    for cand in candidates:
        for pat, dept in _DEPT_HINTS:
            if pat.search(cand):
                return dept
    return None


# ─── Adapter ────────────────────────────────────────────────────────────


def _ext_from_metodist_chunk(chunk: dict | object) -> ExternalBasis | None:
    """Build an ExternalBasis from a Metodist external chunk (dict or
    StandaloneChunk object). Returns None if it doesn't look external."""
    src_url = _get(chunk, "source_url")
    if not src_url or not isinstance(src_url, str) or "://" not in src_url:
        return None
    return ExternalBasis(
        authority=_authority_from_url(src_url) or _get(chunk, "authority"),
        source_url=src_url,
        title=_get(chunk, "document_number") or _get(chunk, "title"),
        snippet=(_get(chunk, "text") or "")[:600],
    )


def _int_from_citation(c: Citation, *, score: float | None = None) -> InternalImpact:
    return InternalImpact(
        document_id=c.document_id,
        title=c.title,
        snippet=c.snippet,
        score=score if score is not None else c.score,
        section=None,
        department=_infer_department(c.title),
    )


def _get(obj: Any, attr: str) -> Any:
    """Read an attribute from either a dict or an object."""
    if isinstance(obj, dict):
        return obj.get(attr)
    return getattr(obj, attr, None)


def _authority_from_url(url: str) -> str | None:
    for host in ("cbu.uz", "lex.uz", "ipakyulibank.uz"):
        if host in url:
            return host
    return None


def build_case_analysis(agg: AgentResult) -> CaseAnalysis:
    """Project the Manager's aggregated AgentResult into a CaseAnalysis.

    Pulls:
      * `summary` from the Metodist text answer if present, otherwise from
        the Searcher's top hit;
      * `affected_internal` from non-confidential citations + Metodist
        internal chunks;
      * `external_basis` from Metodist external chunks (which carry
        authority + source_url);
      * `affected_departments` deduplicated from impacted internal docs.

    Conflicts and recommendations are intentionally left empty here — they
    require the LLM (Metodist) to be prompted for structured output, which
    is a follow-up to this scaffold. The frontend renders them as "—" when
    empty, so the UI is forward-compatible.
    """
    payload = agg.payload or {}
    agents: dict[str, Any] = payload.get("agents", {})

    # Summary — Metodist text wins, falls back to the Searcher's best
    # snippet, then to a generic placeholder.
    summary = ""
    metodist = agents.get("AI Metodist") or {}
    if isinstance(metodist, dict):
        summary = (metodist.get("text") or "").strip()
    if not summary:
        searcher = agents.get("AI Searcher") or {}
        matches = searcher.get("matches") if isinstance(searcher, dict) else None
        if isinstance(matches, list) and matches:
            summary = str(matches[0].get("snippet", ""))[:600]

    # Internal impacts — from citations on the aggregate. Drop entries that
    # have been shadow-guarded down to nothing (no document_id / title /
    # snippet) so the panel doesn't render empty bullets.
    affected_internal: list[InternalImpact] = []
    for c in agg.citations:
        if not c.snippet:
            continue
        if c.document_id is None and c.title is None:
            # Confidential origin — keep the snippet, leave ids None.
            pass
        affected_internal.append(_int_from_citation(c))

    # External basis — Metodist external chunks (lex.uz / cbu.uz / …).
    external_basis: list[ExternalBasis] = []
    if isinstance(metodist, dict):
        # The wrapper currently surfaces counts only. When the standalone
        # is upgraded to return the chunk list directly, this loop will
        # pick them up; for now we look for either layout.
        for raw in metodist.get("external_chunks") or []:
            eb = _ext_from_metodist_chunk(raw)
            if eb:
                external_basis.append(eb)

    # Departments — dedupe in insertion order.
    seen: set[str] = set()
    affected_departments: list[str] = []
    for imp in affected_internal:
        if imp.department and imp.department not in seen:
            seen.add(imp.department)
            affected_departments.append(imp.department)

    return CaseAnalysis(
        summary=summary,
        affected_internal=affected_internal,
        external_basis=external_basis,
        conflicts=[],
        recommendations=[],
        affected_departments=affected_departments,
    )
