"""Stage 7+8+9: persist chunks to Postgres, write Processed\\<id>\\chunks.jsonl,
and the human-readable Markdown sidecar Processed\\<id>\\source.md.

The Markdown sidecar carries YAML-ish frontmatter (title, document_id,
sha256, category, authority, source_url, ingested_at, headings) followed
by the normalized full text. It exists so an operator can browse what
AI Regulyator pulled in and what AI Architect ingested — without ever
opening the raw PDF / DOCX — and so the whole KB is grep-able from
the file system.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from sqlalchemy import delete, select, update

from app.config import get_settings
from app.db.models import Document, DocumentChunk
from app.db.session import session_scope
from app.pipeline.chunker import Chunk
from app.security.paths import safe_join


def _esc(v: str | None) -> str:
    if v is None:
        return '""'
    return '"' + v.replace('"', '\\"').replace("\n", " ") + '"'


def _frontmatter(doc: Document, headings: list[str]) -> str:
    """Minimal YAML-style frontmatter for the Markdown sidecar."""
    lines = [
        "---",
        f"title: {_esc(doc.title)}",
        f"document_id: {doc.id}",
        f"sha256: {doc.sha256}",
        f"category: {_esc(doc.category)}",
        f"authority: {_esc(doc.authority)}",
        f"source_url: {_esc(doc.source_url)}",
        f"raw_path: {_esc(doc.raw_path)}",
        f"status: {_esc(doc.status)}",
        f"is_confidential: {str(doc.is_confidential).lower()}",
        f"ingested_at: {doc.ingested_at.isoformat() if doc.ingested_at else ''}",
    ]
    if headings:
        lines.append("headings:")
        for h in headings[:50]:  # cap so an outlier doc doesn't bloat the file
            lines.append(f"  - {_esc(h)}")
    lines.append("---")
    return "\n".join(lines)


async def persist_chunks(
    document_id: uuid.UUID,
    chunks: list[Chunk],
    embeddings: list[list[float]],
    *,
    full_text: str | None = None,
    headings: list[str] | None = None,
) -> Path:
    """Persist embeddings to Postgres and write the two sidecar files.

    Returns the path of the chunks JSONL (kept as the "primary" processed
    artefact for downstream consumers); the Markdown sidecar sits next to
    it as ``source.md``.
    """
    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings length mismatch")

    s = get_settings()
    processed_dir = safe_join(s.kb_processed, str(document_id))
    processed_dir.mkdir(parents=True, exist_ok=True)
    chunks_path = processed_dir / "chunks.jsonl"
    md_path = processed_dir / "source.md"

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
            .values(processed_path=str(chunks_path))
        )
        # Re-read the document with its server defaults populated
        # (ingested_at) so the Markdown frontmatter carries real values.
        doc = await session.scalar(select(Document).where(Document.id == document_id))

    # JSONL — the existing primary artefact for downstream consumers.
    with chunks_path.open("w", encoding="utf-8") as f:
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

    # Markdown sidecar — operator-readable, grep-able full text. We skip
    # this for confidential (Lotus) documents because the Processed tree
    # is not ACL-restricted the way KB\Lotus\ is, and the Shadow-guard
    # contract forbids id / title / source_url from leaving the agent
    # boundary. Confidential chunks still land in the DB so Shadow can
    # serve summaries, but no Markdown leak vector hits the filesystem.
    if doc is None:
        body = full_text if full_text is not None else "\n\n".join(ch.text for ch in chunks)
        md_path.write_text(body, encoding="utf-8")
    elif not doc.is_confidential:
        body = full_text if full_text is not None else "\n\n".join(ch.text for ch in chunks)
        md_path.write_text(
            _frontmatter(doc, headings or []) + "\n\n" + body + "\n",
            encoding="utf-8",
        )

    return chunks_path
