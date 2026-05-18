"""Stage 7+8: persist chunks to Postgres and write Processed\\<id>\\chunks.jsonl."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from sqlalchemy import delete, update

from app.config import get_settings
from app.db.models import Document, DocumentChunk
from app.db.session import session_scope
from app.pipeline.chunker import Chunk
from app.security.paths import safe_join


async def persist_chunks(
    document_id: uuid.UUID,
    chunks: list[Chunk],
    embeddings: list[list[float]],
) -> Path:
    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings length mismatch")

    s = get_settings()
    processed_dir = safe_join(s.kb_processed, str(document_id))
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_path = processed_dir / "chunks.jsonl"

    async with session_scope() as session:
        # Idempotency: replace any prior chunks for this document.
        await session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        for ch, vec in zip(chunks, embeddings, strict=True):
            session.add(
                DocumentChunk(
                    document_id=document_id,
                    chunk_index=ch.index,
                    content=ch.text,
                    token_count=ch.token_count,
                    embedding=vec,
                    content_hash=ch.content_hash,
                    section_path=ch.section_path,
                )
            )
        await session.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(processed_path=str(out_path))
        )

    with out_path.open("w", encoding="utf-8") as f:
        for ch in chunks:
            f.write(
                json.dumps(
                    {
                        "index": ch.index,
                        "tokens": ch.token_count,
                        "hash": ch.content_hash,
                        "section": ch.section_path,
                        "text": ch.text,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    return out_path
