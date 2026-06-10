"""AI Searcher — semantic search over pgvector.

Embeds the user query, runs HNSW cosine top-k against `document_chunks`,
joins the originating document for metadata, and caches the response in
Redis keyed by (normalized query, role) so warm hits stay well under
the 3-second budget.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict

from sqlalchemy import select

import redis.asyncio as redis_asyncio

from app.agents.base import Agent, AgentContext, AgentResult, Citation
from app.config import get_settings
from app.db.models import Document, DocumentChunk
from app.db.session import session_scope
from app.llm.embeddings import embed_texts

DEFAULT_K = 8
_CACHE_TTL_S = 3600


def _norm(q: str) -> str:
    return " ".join(q.lower().strip().split())


def _cache_key(query: str, role: str) -> str:
    digest = hashlib.sha256(f"{role}|{_norm(query)}".encode()).hexdigest()
    return f"aim:search:{digest}"


class Searcher(Agent):
    name = "AI Searcher"

    def __init__(self) -> None:
        self._redis: redis_asyncio.Redis | None = None

    def _r(self) -> redis_asyncio.Redis:
        if self._redis is None:
            self._redis = redis_asyncio.from_url(get_settings().redis_url, decode_responses=True)
        return self._redis

    async def run(self, ctx: AgentContext) -> AgentResult:
        start = time.perf_counter()
        key = _cache_key(ctx.query, ctx.role)
        cached = await self._r().get(key)
        if cached:
            data = json.loads(cached)
            return AgentResult(
                agent=self.name,
                payload=data["payload"],
                citations=[Citation(**c) for c in data["citations"]],
                confidence=data["confidence"],
                ms_elapsed=int((time.perf_counter() - start) * 1000),
                confidential_origin=data.get("confidential_origin", False),
            )

        vectors = await embed_texts([ctx.query])
        qvec = vectors[0]

        async with session_scope() as session:
            stmt = (
                select(
                    DocumentChunk,
                    Document,
                    DocumentChunk.embedding.cosine_distance(qvec).label("dist"),
                )
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(Document.status == "active")
                .order_by("dist")
                .limit(DEFAULT_K)
            )
            rows = (await session.execute(stmt)).all()

        citations: list[Citation] = []
        confidential = False
        for chunk_row, doc_row, dist in rows:
            if doc_row.is_confidential:
                confidential = True
            citations.append(
                Citation(
                    document_id=None if doc_row.is_confidential else str(doc_row.id),
                    title=None if doc_row.is_confidential else doc_row.title,
                    snippet=chunk_row.content[:600],
                    score=1.0 - float(dist),
                )
            )

        payload = {
            "matches": [
                {"snippet": c.snippet, "score": c.score, "title": c.title}
                for c in citations
            ],
        }

        await self._r().set(
            key,
            json.dumps(
                {
                    "payload": payload,
                    "citations": [asdict(c) for c in citations],
                    "confidence": citations[0].score if citations else 0.0,
                    "confidential_origin": confidential,
                }
            ),
            ex=_CACHE_TTL_S,
        )

        return AgentResult(
            agent=self.name,
            payload=payload,
            citations=citations,
            confidence=citations[0].score if citations else 0.0,
            ms_elapsed=int((time.perf_counter() - start) * 1000),
            confidential_origin=confidential,
        )


searcher = Searcher()
