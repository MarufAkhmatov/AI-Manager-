"""In-memory attachment store for chat uploads.

Operator uploads a letter / circular / contract draft via the chat
panel. The file lands in ``KB\\Temp\\attachments\\<id>\\<filename>``,
runs through the existing OCR pipeline once, and the extracted text
is stashed in this in-process cache keyed by an opaque attachment id.

The cache is intentionally process-local + bounded (LRU) — attachments
are ephemeral and not part of the indexed KB. If you want to keep a
document permanently, drop it into ``KB\\Raw\\`` instead and let
AI Architect's watcher run the full ingestion pipeline.

Entries are purged ``TTL_SECONDS`` after upload (24h default — matches
the CLAUDE.md rule that ``Temp\\`` is purged daily).
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

# Cap so a misbehaving frontend can't pin GBs of attachments in memory.
MAX_ENTRIES = 64
TTL_SECONDS = 24 * 60 * 60  # 24h, matches the Temp\ purge rule
MAX_TEXT_CHARS = 200_000    # ~50 pages — anything bigger truncates


@dataclass(slots=True)
class Attachment:
    id: str
    filename: str
    bytes_size: int
    char_count: int
    text: str
    stored_path: Path
    uploaded_at: float


class _Store:
    def __init__(self) -> None:
        self._entries: OrderedDict[str, Attachment] = OrderedDict()
        self._lock = asyncio.Lock()

    async def put(
        self,
        *,
        filename: str,
        bytes_size: int,
        text: str,
        stored_path: Path,
    ) -> Attachment:
        async with self._lock:
            await self._evict_expired_locked()
            att = Attachment(
                id=uuid.uuid4().hex,
                filename=filename,
                bytes_size=bytes_size,
                char_count=len(text),
                text=text[:MAX_TEXT_CHARS],
                stored_path=stored_path,
                uploaded_at=time.time(),
            )
            self._entries[att.id] = att
            # Hard cap: drop oldest to make room.
            while len(self._entries) > MAX_ENTRIES:
                self._entries.popitem(last=False)
            return att

    async def get(self, attachment_id: str) -> Attachment | None:
        async with self._lock:
            await self._evict_expired_locked()
            att = self._entries.get(attachment_id)
            if att:
                # Move to MRU end so frequent refs keep it alive.
                self._entries.move_to_end(attachment_id)
            return att

    async def _evict_expired_locked(self) -> None:
        cutoff = time.time() - TTL_SECONDS
        dead = [k for k, v in self._entries.items() if v.uploaded_at < cutoff]
        for k in dead:
            self._entries.pop(k, None)


store = _Store()
