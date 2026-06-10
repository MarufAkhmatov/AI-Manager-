"""AI Shadow — Lotus-only retrieval with metadata stripping.

Shadow only ever queries documents where `is_confidential = true`. Its
output is restricted to `{summary, date, authority}` per chunk; the
document id, title, path, and source are never returned. Shadow-guard
(in AI Secure) re-applies the rule as a belt-and-braces second check.
"""

from __future__ import annotations

import time

from sqlalchemy import select

from app.agents.base import Agent, AgentContext, AgentResult, Citation
from app.db.models import Document, DocumentChunk
from app.db.session import session_scope
from app.llm.embeddings import embed_texts

DEFAULT_K = 5


class Shadow(Agent):
    name = "AI Shadow"

    async def run(self, ctx: AgentContext) -> AgentResult:
        start = time.perf_counter()

        if ctx.role == "viewer":
            # Viewers are not permitted to see Lotus content at all.
            return AgentResult(
                agent=self.name,
                payload={"items": [], "denied": True},
                citations=[],
                confidence=0.0,
                ms_elapsed=int((time.perf_counter() - start) * 1000),
                confidential_origin=False,
            )

        qvec = (await embed_texts([ctx.query]))[0]

        async with session_scope() as session:
            stmt = (
                select(
                    DocumentChunk.content,
                    Document.issued_at,
                    Document.authority,
                    DocumentChunk.embedding.cosine_distance(qvec).label("dist"),
                )
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(Document.is_confidential.is_(True))
                .where(Document.status == "active")
                .order_by("dist")
                .limit(DEFAULT_K)
            )
            rows = (await session.execute(stmt)).all()

        items: list[dict] = []
        citations: list[Citation] = []
        for content, issued_at, authority, dist in rows:
            summary = content[:400]
            items.append(
                {
                    "summary": summary,
                    "date": issued_at.isoformat() if issued_at else None,
                    "authority": authority,
                }
            )
            citations.append(
                Citation(
                    document_id=None,  # never expose Lotus document_id
                    title=None,
                    snippet=summary,
                    score=1.0 - float(dist),
                )
            )

        return AgentResult(
            agent=self.name,
            payload={"items": items},
            citations=citations,
            confidence=items and (1.0 - float(rows[0].dist)) or 0.0,
            ms_elapsed=int((time.perf_counter() - start) * 1000),
            confidential_origin=bool(items),
        )


shadow = Shadow()
