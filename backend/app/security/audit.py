"""Append-only hash-chained audit log at Logs\\audit\\audit.jsonl.

Each record carries the sha256 of the previous record's full JSON line,
so any tampering with an earlier entry (rewrite, truncate, reorder) is
detectable by re-walking the chain. The verifier is a tiny standalone
script (`scripts/verify_audit.py`).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.security.paths import safe_join

_lock = asyncio.Lock()


def _path() -> Path:
    s = get_settings()
    audit_dir = safe_join(s.logs, "audit")
    audit_dir.mkdir(parents=True, exist_ok=True)
    return audit_dir / "audit.jsonl"


def _last_hash(path: Path) -> str:
    if not path.exists() or path.stat().st_size == 0:
        return "0" * 64
    with path.open("rb") as f:
        try:
            f.seek(-4096, 2)
        except OSError:
            f.seek(0)
        tail = f.read().splitlines()
    if not tail:
        return "0" * 64
    return hashlib.sha256(tail[-1]).hexdigest()


async def record(event: str, **fields: Any) -> None:
    """Append a structured event. Safe under concurrent callers (asyncio lock)."""
    path = _path()
    async with _lock:
        prev = _last_hash(path)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "prev": prev,
            **fields,
        }
        line = json.dumps(entry, ensure_ascii=False, sort_keys=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def verify(path: Path | None = None) -> tuple[bool, int, str | None]:
    """Walk the chain. Returns (ok, lines_checked, first_bad_line_or_None)."""
    p = path or _path()
    if not p.exists():
        return True, 0, None
    prev = "0" * 64
    n = 0
    with p.open("rb") as f:
        for raw in f:
            n += 1
            try:
                entry = json.loads(raw)
            except Exception:
                return False, n, raw.decode("utf-8", errors="ignore").strip()
            if entry.get("prev") != prev:
                return False, n, raw.decode("utf-8", errors="ignore").strip()
            prev = hashlib.sha256(raw.rstrip(b"\n")).hexdigest()
    return True, n, None
