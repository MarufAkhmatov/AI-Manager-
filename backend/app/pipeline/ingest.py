"""Stage 1+2: ingest + classify.

Ingestion is write-once. We compute the sha256 of the source file, dedupe
against `documents.sha256`, and (for new files) copy the binary into
`KB\\Raw\\<doc_id>\\original.<ext>`. Files that arrived already inside
`KB\\Lotus\\` are *moved* (not copied) into the Lotus authority/year layout
so the original location doesn't leak as a side path.
"""

from __future__ import annotations

import hashlib
import shutil
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import select

from app.config import get_settings
from app.db.models import Document
from app.db.session import session_scope
from app.pipeline.classify import classify
from app.security.paths import safe_join


@dataclass(slots=True)
class IngestResult:
    document_id: uuid.UUID
    raw_path: Path
    already_indexed: bool


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _route_lotus(src: Path, authority: str | None) -> Path:
    s = get_settings()
    year = str(date.today().year)
    sub = authority or "unknown"
    dest_dir = safe_join(s.kb_lotus, sub, year)
    dest_dir.mkdir(parents=True, exist_ok=True)
    return dest_dir / src.name


def _route_raw(doc_id: uuid.UUID, src: Path) -> Path:
    s = get_settings()
    dest_dir = safe_join(s.kb_raw, str(doc_id))
    dest_dir.mkdir(parents=True, exist_ok=True)
    return dest_dir / f"original{src.suffix.lower()}"


async def ingest_file(src: Path) -> IngestResult:
    """Idempotent ingest of a file already present somewhere under AIM_ROOT.

    For Lotus inputs the file is *relocated* into the canonical Lotus tree.
    For all other inputs the file is copied (preserved) into KB\\Raw\\.
    Returns the document_id and whether it was already known.
    """
    s = get_settings()
    src = src.resolve()
    # Reject anything outside the root before we touch state.
    src.relative_to(s.aim_root.resolve())

    digest = _sha256(src)

    async with session_scope() as session:
        existing = await session.scalar(select(Document).where(Document.sha256 == digest))
        if existing is not None:
            return IngestResult(
                document_id=existing.id,
                raw_path=Path(existing.raw_path),
                already_indexed=True,
            )

        cls = classify(src)
        doc_id = uuid.uuid4()

        if cls.category == "lotus":
            stored = _route_lotus(src, cls.authority)
            shutil.move(str(src), str(stored))
        else:
            stored = _route_raw(doc_id, src)
            if src != stored:
                shutil.copy2(str(src), str(stored))

        doc = Document(
            id=doc_id,
            sha256=digest,
            title=src.stem,
            category=cls.category,
            authority=cls.authority,
            source_url=None,
            raw_path=str(stored),
            status="active",
            is_confidential=cls.is_confidential,
        )
        session.add(doc)

    return IngestResult(document_id=doc_id, raw_path=stored, already_indexed=False)
