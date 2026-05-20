"""Structured extraction of conflicts + recommendations.

AI Metodist (the standalone) returns a free-form narrative answer. The
operator's flagship cases (incoming-letter analysis, product compliance,
normative audit) want that narrative distilled into two machine-readable
lists:

  * `conflicts`        — internal clause ⇄ external act clashes
  * `recommendations`  — concrete amend / draft / withdraw actions

This module runs a second, cheap LLM pass (local Ollama `qwen2.5` —
no Anthropic tokens) that reads the summary + retrieved internal docs +
external acts and returns those two lists as JSON. It is deliberately
best-effort: a missing Ollama, a model timeout, or malformed JSON all
degrade to empty lists, leaving the base CaseAnalysis intact.

In `AIM_DEMO=1` mode there is no Ollama, so we synthesise deterministic
but context-aware stubs from the inputs so the UI shows the full shape.
"""

from __future__ import annotations

import json
import re

from app.agents.cases import CaseAnalysis, Conflict, Recommendation
from app.config import get_settings
from app.events import emit
from app.llm.ollama_client import get_ollama

# Keep the extraction prompt's inputs bounded so a huge attachment doesn't
# blow the local model's context window.
_MAX_DOCS = 6
_SNIPPET_CHARS = 400
_LLM_TIMEOUT_S = 12.0

_SYSTEM = (
    "You are a banking compliance analyst for an Uzbek bank. "
    "Given a question, an analysis summary, the bank's internal documents, "
    "and external normative acts (lex.uz / cbu.uz / ipakyulibank.uz), you "
    "extract (1) concrete CONFLICTS where an internal clause clashes with an "
    "external requirement, and (2) concrete RECOMMENDATIONS the analyst should "
    "act on. Respond with STRICT JSON only — no prose, no markdown fences. "
    "Schema:\n"
    '{"conflicts":[{"internal_ref":str,"external_ref":str,"why":str}],'
    '"recommendations":[{"action":str,"target_doc":str,"target_clause":str,'
    '"suggested_text":str}]}\n'
    "action must be one of: amend, draft, withdraw, review. Keep each field "
    "under 300 characters. If you cannot find a real conflict, return an "
    "empty conflicts list — do not invent one. Answer in the same language "
    "as the question (Uzbek or Russian)."
)


def _clip(s: str | None, n: int = _SNIPPET_CHARS) -> str:
    if not s:
        return ""
    return s[:n]


def _build_prompt(case: CaseAnalysis, query: str, directive: str = "") -> str:
    lines: list[str] = [f"QUESTION:\n{query.strip()[:1500]}", ""]
    if directive:
        lines += [f"TASK DIRECTIVE:\n{directive[:500]}", ""]
    if case.summary:
        lines += ["ANALYSIS SUMMARY:", case.summary[:1500], ""]

    lines.append("INTERNAL DOCUMENTS:")
    if case.affected_internal:
        for i, it in enumerate(case.affected_internal[:_MAX_DOCS], 1):
            ref = it.title or "(internal doc)"
            dept = f" [{it.department}]" if it.department else ""
            lines.append(f"  {i}. {ref}{dept}: {_clip(it.snippet)}")
    else:
        lines.append("  (none retrieved)")
    lines.append("")

    lines.append("EXTERNAL ACTS:")
    if case.external_basis:
        for i, ex in enumerate(case.external_basis[:_MAX_DOCS], 1):
            ref = ex.title or ex.authority or "(external act)"
            url = f" <{ex.source_url}>" if ex.source_url else ""
            lines.append(f"  {i}. {ref}{url}: {_clip(ex.snippet)}")
    else:
        lines.append("  (none retrieved)")
    lines.append("")
    lines.append("Return the JSON now.")
    return "\n".join(lines)


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse(raw: str) -> tuple[list[Conflict], list[Recommendation]]:
    """Parse the model's JSON, tolerating code fences and surrounding prose."""
    text = _FENCE_RE.sub("", raw).strip()
    if not text:
        return [], []
    # Grab the first {...} block if the model added chatter around it.
    if not text.startswith("{"):
        m = _OBJ_RE.search(text)
        if not m:
            return [], []
        text = m.group(0)
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return [], []

    conflicts: list[Conflict] = []
    for c in (data.get("conflicts") or [])[:20]:
        if not isinstance(c, dict):
            continue
        why = str(c.get("why", "")).strip()
        if not why:
            continue
        conflicts.append(
            Conflict(
                internal_ref=str(c.get("internal_ref", "")).strip()[:300],
                external_ref=str(c.get("external_ref", "")).strip()[:300],
                why=why[:300],
            )
        )

    recs: list[Recommendation] = []
    _ALLOWED = {"amend", "draft", "withdraw", "review"}
    for r in (data.get("recommendations") or [])[:20]:
        if not isinstance(r, dict):
            continue
        suggested = str(r.get("suggested_text", "")).strip()
        if not suggested:
            continue
        action = str(r.get("action", "review")).strip().lower()
        if action not in _ALLOWED:
            action = "review"
        recs.append(
            Recommendation(
                action=action,
                target_doc=(str(r["target_doc"]).strip()[:300] if r.get("target_doc") else None),
                target_clause=(str(r["target_clause"]).strip()[:120] if r.get("target_clause") else None),
                suggested_text=suggested[:600],
            )
        )
    return conflicts, recs


def _demo_extract(case: CaseAnalysis, query: str) -> tuple[list[Conflict], list[Recommendation]]:
    """Deterministic, context-aware stubs for AIM_DEMO=1.

    Pairs each external act with the most relevant internal doc to fabricate
    a plausible-looking conflict, and proposes an amend recommendation per
    affected internal doc — enough to populate the UI sections meaningfully
    without an LLM."""
    conflicts: list[Conflict] = []
    internals = case.affected_internal[:3]
    externals = case.external_basis[:3]
    for i, ex in enumerate(externals):
        internal = internals[i] if i < len(internals) else (internals[0] if internals else None)
        internal_ref = (internal.title if internal and internal.title else "ichki normativ hujjat")
        external_ref = ex.title or ex.authority or "tashqi normativ akt"
        conflicts.append(
            Conflict(
                internal_ref=internal_ref,
                external_ref=external_ref,
                why=(
                    f"(demo) Ichki hujjatdagi tegishli band {external_ref} "
                    "talablariga to'liq muvofiq emas — yangi koeffitsiyent/"
                    "stavka qiymatlari aks ettirilmagan."
                ),
            )
        )

    recs: list[Recommendation] = []
    for internal in internals:
        target = internal.title or "ichki normativ hujjat"
        recs.append(
            Recommendation(
                action="amend",
                target_doc=target,
                target_clause=internal.section,
                suggested_text=(
                    f"(demo) {target} hujjatining tegishli bandini tashqi "
                    "normativ talablariga moslab yangilang: qiymatlar, "
                    "muddatlar va javobgar departamentni aniqlashtiring."
                ),
            )
        )
    if not recs and case.summary:
        recs.append(
            Recommendation(
                action="review",
                target_doc=None,
                target_clause=None,
                suggested_text=(
                    "(demo) Tegishli ichki normativ hujjatlarni qo'lda ko'rib "
                    "chiqing — retrieval bo'sh natija qaytardi."
                ),
            )
        )
    return conflicts, recs


async def enrich_case_analysis(
    case: CaseAnalysis, *, query: str, directive: str = ""
) -> CaseAnalysis:
    """Fill `case.conflicts` + `case.recommendations` in place and return it.

    Skips the LLM call entirely when there's nothing to analyse (no
    internal docs and no external acts). Best-effort: any failure leaves
    the lists empty. `directive` is the per-case instruction (from the
    workflow template) folded into the prompt to steer the output shape.
    """
    if case.conflicts or case.recommendations:
        return case  # already populated upstream
    if not case.affected_internal and not case.external_basis:
        return case  # nothing to compare

    settings = get_settings()
    if settings.aim_demo:
        case.conflicts, case.recommendations = _demo_extract(case, query)
        return case

    import asyncio

    prompt = _build_prompt(case, query, directive)
    try:
        raw = await asyncio.wait_for(
            get_ollama().generate(
                settings.ollama_model_router,
                prompt,
                system=_SYSTEM,
                options={"temperature": 0.1},
            ),
            timeout=_LLM_TIMEOUT_S,
        )
        case.conflicts, case.recommendations = _parse(raw)
    except (TimeoutError, asyncio.TimeoutError):
        await emit("AI Metodist", "extract.timeout")
    except Exception as e:  # Ollama down, network, bad JSON path, …
        await emit("AI Metodist", "extract.error", error=f"{type(e).__name__}: {e}")
    return case
