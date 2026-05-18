"""AI Architect — owner of the filesystem + pipeline lifecycle.

Architect is not on the user query path; it runs as a background
service. It performs:

  1. an initial full scan of AIM_ROOT at boot,
  2. starts the watchdog observer for live changes,
  3. exposes a `reindex` helper for admin-triggered rescans.
"""

from __future__ import annotations

import asyncio

from app.events import emit
from app.watcher.fs_watch import start_observer
from app.watcher.scanner import initial_scan


class Architect:
    name = "AI Architect"

    def __init__(self) -> None:
        self._observer = None
        self._initial_task: asyncio.Task | None = None

    async def boot(self) -> None:
        await emit(self.name, "boot.start")
        # Initial scan runs in a background task so the API can serve.
        self._initial_task = asyncio.create_task(initial_scan())
        self._observer = start_observer()
        await emit(self.name, "boot.done")

    async def shutdown(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
        if self._initial_task is not None and not self._initial_task.done():
            self._initial_task.cancel()
        await emit(self.name, "shutdown.done")

    async def reindex(self) -> int:
        """Admin-triggered full rescan. Returns count of files processed."""
        await emit(self.name, "reindex.start")
        count = await initial_scan()
        await emit(self.name, "reindex.done", processed=count)
        return count


architect = Architect()
