"""Intent classification — which specialist agents should run + case type.

Two layers:

  * `_rule_based()` — the keyword heuristic (EN + RU + UZ). Fast,
    deterministic, no I/O. Always the fallback.
  * `detect_intent()` — in the real stack, asks the local Ollama
    `qwen2.5` to classify the query into (agents, case_type) as JSON.
    Catches everything that the keyword list misses (paraphrases,
    mixed-language, implicit intent) while still degrading to the rules
    on any failure (Ollama down, timeout, malformed JSON).

`AI Searcher` is always in the plan (every answer wants grounded
citations); `AI Secure` is appended later by the Manager regardless of
the plan. The classifier only decides between Searcher / Shadow /
Metodist and tags a `case_type` for the UI / future per-case workflows.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from app.config import get_settings
from app.events import emit
from app.llm.ollama_client import get_ollama

# Agents the classifier is allowed to schedule on the query path.
QUERY_AGENTS = {"AI Searcher", "AI Shadow", "AI Metodist"}

# Coarse case types — surfaced to the UI and reserved for per-case
# workflow templating later.
CASE_TYPES = {
    "general",          # plain lookup / question
    "incoming_letter",  # a letter / circular to compare against the KB
    "product_check",    # business requirement / new product compliance
    "normative_audit",  # which internal docs need updating
}

_LLM_TIMEOUT_S = 6.0


@dataclass(slots=True)
class IntentDecision:
    agents: set[str] = field(default_factory=lambda: {"AI Searcher"})
    case_type: str = "general"
    source: str = "rules"  # "llm" | "rules"


# ─── Rule-based fallback (also used verbatim in demo mode) ───────────────

_SHADOW_KW = (
    "lotus", "internal", "confidential",
    "внутр", "лотус", "конфиденциальн",
    "ichki", "maxfiy",
)
_METODIST_KW = (
    "compliant", "compliance", "conflict", "gap", "policy", "normative",
    "regulation", "amend", "clause", "requirement",
    "соответств", "конфликт", "нарушени", "норматив", "положени",
    "требовани", "регламент", "пункт",
    "muvofiq", "nizom", "normativ", "qoida", "talab", "siyosat",
    "qiyos", "taqqosla", "band", "hujjat", "muvofiqlash",
    "мувофиқ", "низом", "қоида", "талаб", "сиёсат",
)
_AUDIT_KW = ("audit", "yangila", "update", "обнов", "yangilan", "tekshir")
_PRODUCT_KW = ("produkt", "product", "biznes", "business", "trebovan", "talab", "yangi mahsulot")


def _rule_based(query: str) -> IntentDecision:
    lower = query.lower()
    agents: set[str] = {"AI Searcher"}
    if any(k in lower for k in _SHADOW_KW):
        agents.add("AI Shadow")
    metodist = any(k in lower for k in _METODIST_KW)
    if metodist:
        agents.add("AI Metodist")

    # Coarse case typing for the UI.
    case_type = "general"
    if any(k in lower for k in _PRODUCT_KW) and metodist:
        case_type = "product_check"
    elif any(k in lower for k in _AUDIT_KW) and metodist:
        case_type = "normative_audit"
    elif metodist:
        case_type = "normative_audit"
    return IntentDecision(agents=agents, case_type=case_type, source="rules")


# ─── LLM classifier ──────────────────────────────────────────────────────

_SYSTEM = (
    "You route banking-compliance queries for an Uzbek bank to specialist "
    "AI agents. Decide which of these agents to run:\n"
    "- AI Searcher: semantic search over the knowledge base (ALWAYS include).\n"
    "- AI Shadow: retrieves CONFIDENTIAL internal 'Lotus' documents. Include "
    "only when the query concerns internal/confidential policy.\n"
    "- AI Metodist: normative comparison / conflict / gap analysis. Include "
    "when the query asks about compliance, conflicts, updating documents, or "
    "checking a draft/product against rules.\n"
    "Also classify case_type as one of: general, incoming_letter, "
    "product_check, normative_audit.\n"
    "Respond with STRICT JSON only, no prose:\n"
    '{"agents":["AI Searcher",...],"case_type":"..."}'
)


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse(raw: str) -> IntentDecision | None:
    text = _FENCE_RE.sub("", raw).strip()
    if not text.startswith("{"):
        m = _OBJ_RE.search(text)
        if not m:
            return None
        text = m.group(0)
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None

    raw_agents = data.get("agents")
    if not isinstance(raw_agents, list):
        return None
    agents = {a for a in raw_agents if a in QUERY_AGENTS}
    agents.add("AI Searcher")  # always grounded

    case_type = data.get("case_type", "general")
    if case_type not in CASE_TYPES:
        case_type = "general"
    return IntentDecision(agents=agents, case_type=case_type, source="llm")


async def detect_intent(query: str, *, allow_llm: bool = True) -> IntentDecision:
    """Classify `query`. Uses the local LLM in the real stack, the keyword
    rules in demo mode / when `allow_llm` is False / on any LLM failure."""
    settings = get_settings()
    if settings.aim_demo or not allow_llm or not getattr(settings, "aim_llm_intent", True):
        return _rule_based(query)

    import asyncio

    try:
        raw = await asyncio.wait_for(
            get_ollama().generate(
                settings.ollama_model_router,
                f"QUERY:\n{query[:2000]}\n\nReturn the JSON now.",
                system=_SYSTEM,
                options={"temperature": 0.0},
            ),
            timeout=_LLM_TIMEOUT_S,
        )
    except (TimeoutError, asyncio.TimeoutError):
        await emit("AI Manager", "intent.timeout")
        return _rule_based(query)
    except Exception as e:  # Ollama down / network / etc.
        await emit("AI Manager", "intent.error", error=f"{type(e).__name__}: {e}")
        return _rule_based(query)

    decision = _parse(raw)
    if decision is None:
        return _rule_based(query)
    return decision
