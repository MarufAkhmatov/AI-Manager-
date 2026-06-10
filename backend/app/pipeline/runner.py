"""Orchestrate the pipeline for a single file.

State is recorded per-stage in `processed_files` so retries are safe and
the UI can show progress. Failures are retried with exponential backoff
up to 3 attempts per stage.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, update

from app.config import get_settings
from app.db.models import ProcessedFile
from app.db.session import session_scope
from app.events import emit
from app.llm.embeddings import embed_texts
from app.pipeline.chunker import chunk
from app.pipeline.ingest import ingest_file
from app.pipeline.normalize import normalize
from app.pipeline.ocr import extract_text
from app.pipeline.storage import persist_chunks

STAGES = ("ocr", "normalize", "chunk", "embed", "store")


async def _record(document_id: uuid.UUID, stage: str, status: str, err: str | None = None) -> None:
    async with session_scope() as session:
        row = await session.scalar(
            select(ProcessedFile).where(
                ProcessedFile.document_id == document_id, ProcessedFile.stage == stage
            )
        )
        if row is None:
            row = ProcessedFile(document_id=document_id, stage=stage, status=status)
            session.add(row)
        else:
            row.status = status
            row.last_error = err
            if status == "running":
                row.attempts += 1
                row.started_at = datetime.now(timezone.utc)
            elif status in {"done", "failed"}:
                row.finished_at = datetime.now(timezone.utc)


async def _run_with_retry(coro_factory, *, stage: str, document_id: uuid.UUID):
    attempts, delay = 0, 1.0
    while True:
        attempts += 1
        await _record(document_id, stage, "running")
        try:
            result = await coro_factory()
            await _record(document_id, stage, "done")
            return result
        except Exception as e:
            await _record(document_id, stage, "failed", err=f"{type(e).__name__}: {e}")
            if attempts >= 3:
                raise
            await asyncio.sleep(delay)
            delay *= 2


async def process_file(src: Path) -> uuid.UUID:
    """Run the full ingest + transform + store pipeline for one source file."""
    ingest = await ingest_file(src)
    doc_id = ingest.document_id
    raw = ingest.raw_path

    await emit("AI Architect", "pipeline.start", document_id=str(doc_id))

    if ingest.already_indexed:
        await emit("AI Architect", "pipeline.skip", document_id=str(doc_id), reason="dedupe")
        return doc_id

    text = await _run_with_retry(lambda: extract_text(raw), stage="ocr", document_id=doc_id)
    await emit("AI Architect", "stage.done", document_id=str(doc_id), stage="ocr", chars=len(text))

    norm = await _run_with_retry(
        lambda: asyncio.to_thread(normalize, text), stage="normalize", document_id=doc_id
    )

    chunks = await _run_with_retry(
        lambda: asyncio.to_thread(chunk, norm.text),
        stage="chunk",
        document_id=doc_id,
    )
    if not chunks:
        await emit("AI Architect", "pipeline.empty", document_id=str(doc_id))
        return doc_id

    vectors = await _run_with_retry(
        lambda: embed_texts([c.text for c in chunks]),
        stage="embed",
        document_id=doc_id,
    )

    out_path = await _run_with_retry(
        lambda: persist_chunks(
            doc_id,
            chunks,
            vectors,
            full_text=norm.text,
            headings=norm.headings,
        ),
        stage="store",
        document_id=doc_id,
    )

    await emit(
        "AI Architect",
        "pipeline.done",
        document_id=str(doc_id),
        chunks=len(chunks),
        processed_path=str(out_path),
    )

    # Phase 4 — auto-audit. A freshly-ingested regulator act gets compared
    # against the internal KB straight away, so the operator wakes up to a
    # "these internal docs need updating" finding instead of having to ask.
    # Fire-and-forget: the audit must never hold up or break ingestion.
    if get_settings().aim_auto_audit:
        await _maybe_auto_audit(doc_id, norm.text)

    return doc_id


async def _maybe_auto_audit(document_id: uuid.UUID, text: str) -> None:
    """Trigger a normative audit if the just-ingested doc is a regulator
    act. Looks up category / title / source_url from the DB row Architect
    wrote during ingest."""
    from app.db.models import Document

    async with session_scope() as session:
        doc = await session.scalar(select(Document).where(Document.id == document_id))
    if doc is None or doc.category != "regulator":
        return

    from app.agents.audit import audit_document

    asyncio.create_task(
        audit_document(
            title=doc.title or "external act",
            text=text,
            source_url=doc.source_url,
        )
    )
