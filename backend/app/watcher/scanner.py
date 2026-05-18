"""Initial full scan of AIM_ROOT.

Run once at startup before the live observer begins. Walks every file
under the root and enqueues it through the pipeline. Skips Processed/,
Archive/, Temp/, Logs/, and Cache/ — those are owned by the system.
"""

from __future__ import annotations

from pathlib import Path

from app.config import get_settings
from app.events import emit
from app.pipeline.runner import process_file

_SKIP_DIRS = {"Processed", "Archive", "Temp", "Logs", "Cache"}


def _eligible(path: Path, root: Path) -> bool:
    if not path.is_file():
        return False
    rel = path.relative_to(root)
    return not any(part in _SKIP_DIRS for part in rel.parts)


async def initial_scan() -> int:
    """Process every eligible file under AIM_ROOT. Returns the count processed."""
    s = get_settings()
    root = s.aim_root.resolve()
    if not root.exists():
        await emit("AI Architect", "scan.root_missing", root=str(root))
        return 0

    count = 0
    await emit("AI Architect", "scan.start", root=str(root))
    for p in root.rglob("*"):
        if _eligible(p, root):
            try:
                await process_file(p)
                count += 1
            except Exception as e:
                await emit(
                    "AI Architect",
                    "scan.error",
                    path=str(p),
                    error=f"{type(e).__name__}: {e}",
                )
    await emit("AI Architect", "scan.done", processed=count)
    return count
