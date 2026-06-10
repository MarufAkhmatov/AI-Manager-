"""Per-case workflow templates.

The intent classifier tags each query with a `case_type`. A template then
shapes the run for that case:

  * `extra_agents`   — agents to force into the plan beyond what intent
                       picked (e.g. product checks must consult Shadow for
                       Lotus requirements even if the wording didn't say so).
  * `metodist_mode`  — overrides AI Metodist's ask/compare auto-selection
                       (incoming letters / audits / product checks are all
                       comparisons, not plain Q&A).
  * `directive`      — a short instruction stored in ctx.scratch and folded
                       into the conflict/recommendation extraction prompt so
                       the structured output matches the case's intent.

Templates deliberately do NOT rewrite the Searcher query — Searcher embeds
the user's actual text, and prepending boilerplate would blur the vector.
The framing only steers Metodist + the extraction pass.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class WorkflowTemplate:
    case_type: str
    extra_agents: set[str] = field(default_factory=set)
    metodist_mode: str | None = None          # "ask" | "compare" | None
    directive: str = ""


_TEMPLATES: dict[str, WorkflowTemplate] = {
    "incoming_letter": WorkflowTemplate(
        case_type="incoming_letter",
        extra_agents={"AI Metodist"},
        metodist_mode="compare",
        directive=(
            "Kelgan xat/hujjatni bank ichki normativlari bilan taqqosla. "
            "Qaysi ichki hujjatni, qaysi bandini o'zgartirish kerakligini va "
            "qaysi departament javobgar ekanini ko'rsat."
        ),
    ),
    "product_check": WorkflowTemplate(
        case_type="product_check",
        # A new product must be checked against internal rules, external
        # acts AND confidential Lotus requirements.
        extra_agents={"AI Metodist", "AI Shadow"},
        metodist_mode="compare",
        directive=(
            "Yangi mahsulot/biznes talabni barcha ichki normativlar, lex.uz, "
            "cbu.uz va maxfiy (Lotus) talablar bilan tekshir. Zid joylarni "
            "aniqla va to'g'ri, normativlarga mos yo'lni taklif qil."
        ),
    ),
    "normative_audit": WorkflowTemplate(
        case_type="normative_audit",
        extra_agents={"AI Metodist"},
        metodist_mode="compare",
        directive=(
            "Eng so'nggi tashqi normativ aktlarni bankning ichki hujjatlari "
            "bilan taqqosla. Qaysi ichki hujjatni, qaysi bandini, qaysi manba "
            "(aniq ssilka) asosida yangilash kerakligini ko'rsat."
        ),
    ),
    "general": WorkflowTemplate(case_type="general"),
}


def template_for(case_type: str) -> WorkflowTemplate:
    return _TEMPLATES.get(case_type, _TEMPLATES["general"])
