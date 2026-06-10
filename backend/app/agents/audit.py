"""Auto-audit: compare a newly-ingested external act against internal KB.

Phase 4 trigger flow:

  AI Regulyator downloads a new act  →  AI Architect ingests it
  (OCR → chunk → embed → store)      →  pipeline.done for a `regulator`
  document fires `audit_document()`  →  Manager runs the comparison
  (Searcher internal retrieval + Metodist diff + extract conflicts/recs)
  →  result stored as a Notification  →  WS `audit.finding` wakes the bell.

The audit reuses `manager.chat()` verbatim — same agents, same Secure
egress, same structured CaseAnalysis + conflict/recommendation
extraction — so an auto-audit and a hand-typed Case 3 query produce
identical output. The only difference is who initiated it.
"""

from __future__ import annotations

from app.events import emit
from app.notifications import new_notification
from app.notifications import store as notif_store

# Cap the act text we feed the comparison query so a 200-page regulation
# doesn't blow the agents' input budgets. The first chunk usually carries
# the act's subject + key clauses, which is enough for the retrieval to
# surface the internal docs it touches.
_AUDIT_TEXT_CHARS = 6000


async def audit_document(
    *,
    title: str,
    text: str,
    source_url: str | None,
    role: str = "admin",
) -> str:
    """Run a normative audit for one external act and store the finding.

    Returns the created notification id. Best-effort: if the comparison
    raises (Ollama / DB hiccup) the error is emitted on the WS bus and the
    exception is swallowed so the ingestion pipeline that called us keeps
    running.
    """
    # Imported lazily to avoid a circular import (manager imports nothing
    # from audit, but audit drives manager).
    from app.agents.manager import manager

    await emit("AI Regulyator", "audit.start", title=title[:200])

    query = (
        "Yangi tashqi normativ akt KB'ga qo'shildi. "
        "Bankning qaysi ichki normativ hujjatlarini va qaysi bandlarini "
        "yangilash kerakligini, manbalari bilan ko'rsating.\n\n"
        f"--- Akt: {title} ---\n"
        f"{(text or '')[:_AUDIT_TEXT_CHARS]}"
    )

    try:
        result = await manager.chat(query=query, user_id=None, role=role)
    except Exception as e:  # noqa: BLE001 — must not break the pipeline
        await emit(
            "AI Regulyator",
            "audit.error",
            title=title[:200],
            error=f"{type(e).__name__}: {e}",
        )
        return ""

    case = result.get("case_analysis") or {}
    summary = (case.get("summary") or "").strip() or f"Audit: {title}"

    notif = new_notification(
        kind="audit",
        title=title,
        source_url=source_url,
        summary=summary[:400],
        case_analysis=case,
    )
    await notif_store.add(notif)
    await emit(
        "AI Regulyator",
        "audit.finding",
        notification_id=notif.id,
        title=title[:200],
        conflicts=len(case.get("conflicts") or []),
        recommendations=len(case.get("recommendations") or []),
    )
    return notif.id
