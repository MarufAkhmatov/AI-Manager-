"""Live filesystem observer.

Bridges the synchronous `watchdog` callbacks into our asyncio pipeline.
Files arriving in `Processed/`, `Cache/`, `Logs/`, `Temp/`, or
`Archive/` are ignored — those directories belong to the system itself.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from app.config import get_settings
from app.events import emit
from app.pipeline.runner import process_file

_SKIP_DIRS = {"Processed", "Archive", "Temp", "Logs", "Cache"}


class _Handler(FileSystemEventHandler):
    def __init__(self, loop: asyncio.AbstractEventLoop, root: Path) -> None:
        self._loop = loop
        self._root = root

    def _interesting(self, src_path: str) -> Path | None:
        p = Path(src_path)
        try:
            rel = p.resolve().relative_to(self._root.resolve())
        except ValueError:
            return None
        if any(part in _SKIP_DIRS for part in rel.parts):
            return None
        if not p.is_file():
            return None
        return p

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        target = self._interesting(event.src_path)
        if target is None:
            return
        asyncio.run_coroutine_threadsafe(self._dispatch(target), self._loop)

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        dest = getattr(event, "dest_path", None)
        if not dest:
            return
        target = self._interesting(dest)
        if target is None:
            return
        asyncio.run_coroutine_threadsafe(self._dispatch(target), self._loop)

    async def _dispatch(self, path: Path) -> None:
        try:
            await process_file(path)
        except Exception as e:
            await emit(
                "AI Architect",
                "watch.error",
                path=str(path),
                error=f"{type(e).__name__}: {e}",
            )


def start_observer() -> Observer:
    s = get_settings()
    root = s.aim_root.resolve()
    loop = asyncio.get_running_loop()
    observer = Observer()
    observer.schedule(_Handler(loop, root), str(root), recursive=True)
    observer.start()
    return observer
