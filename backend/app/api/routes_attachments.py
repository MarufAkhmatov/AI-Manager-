"""/api/chat/attachments — upload a letter / circular / draft for analysis.

Reusable across the three Case workflows in the operator's spec:
  * Case 1 (yangi xat) — incoming regulator letter
  * Case 2 (yangi produkt) — business requirement draft
  * Case 3 (audit) — external act to cross-check

The file is OCR-extracted once and the text is kept in process memory
(``app.attachments.store``) keyed by an opaque ``attachment_id``. The
caller then includes that id on the subsequent ``POST /api/chat`` so
Manager can fold the text into its query context.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app import attachments
from app.config import get_settings
from app.deps import AuthUser, current_user
from app.pipeline.ocr import extract_text
from app.security.paths import safe_join

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Cap upload size at 25 MB — matches the indexable doc size used by the
# real pipeline; anything larger is almost always a scanned book that the
# operator should drop into KB\Raw\ for proper ingestion.
MAX_BYTES = 25 * 1024 * 1024
ALLOWED_EXT = {".pdf", ".docx", ".doc", ".txt", ".md", ".png", ".jpg", ".jpeg", ".tiff"}


@router.post("/attachments")
async def upload_attachment(
    file: UploadFile = File(...),
    user: AuthUser = Depends(current_user),
) -> dict:
    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"file exceeds {MAX_BYTES // (1024 * 1024)} MB limit",
        )

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXT:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"unsupported file type: {suffix or '(no extension)'}",
        )

    # Land the file under KB\Temp\attachments\<batch>\ — Temp is auto-purged
    # daily (CLAUDE.md), so we never accidentally retain user uploads.
    s = get_settings()
    batch = uuid.uuid4().hex
    target_dir = safe_join(s.kb_temp, "attachments", batch)
    target_dir.mkdir(parents=True, exist_ok=True)
    # Sanitise filename: strip directory components, keep base + suffix.
    safe_name = Path(file.filename or f"upload{suffix}").name
    target = target_dir / safe_name
    target.write_bytes(raw)

    try:
        text = await extract_text(target)
    except Exception as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"could not extract text: {type(e).__name__}: {e}",
        ) from e

    att = await attachments.store.put(
        filename=safe_name,
        bytes_size=len(raw),
        text=text,
        stored_path=target,
    )
    preview = att.text[:400]
    return {
        "attachment_id": att.id,
        "filename": att.filename,
        "bytes_size": att.bytes_size,
        "char_count": att.char_count,
        "preview": preview,
    }
