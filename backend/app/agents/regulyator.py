"""AI Regulyator — daily crawl + supersede.

Runs three site crawlers, deduplicates discovered documents by URL +
sha256 against `documents`, writes new artefacts into
`KB\\Regulator\\<bucket>\\` (the watcher picks them up and runs the
pipeline), and marks any previous revision sharing the same source_url
as `status='deprecated'` + relocates the file to `Archive\\<YYYY-MM>\\`.
"""

from __future__ import annotations

import hashlib
import shutil
from datetime import date
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, update

from app.config import get_settings
from app.crawler.base import BaseCrawler
from app.crawler.cbu_uz import CbuUzCrawler
from app.crawler.ipakyulibank import IpakYuliCrawler
from app.crawler.lex_uz import LexUzCrawler
from app.db.models import Document
from app.db.session import session_scope
from app.events import emit
from app.security.paths import safe_join


def _bucket_dir(bucket: str) -> Path:
    s = get_settings()
    p = safe_join(s.kb_regulator, bucket)
    p.mkdir(parents=True, exist_ok=True)
    return p


async def _supersede(source_url: str) -> None:
    """Move any prior active version with the same source_url to Archive."""
    s = get_settings()
    async with session_scope() as session:
        rows = (
            await session.execute(
                select(Document).where(
                    Document.source_url == source_url, Document.status == "active"
                )
            )
        ).scalars().all()
        if not rows:
            return
        archive_dir = safe_join(s.archive, date.today().strftime("%Y-%m"))
        archive_dir.mkdir(parents=True, exist_ok=True)
        for r in rows:
            raw = Path(r.raw_path)
            if raw.exists():
                shutil.move(str(raw), str(archive_dir / raw.name))
            await session.execute(
                update(Document).where(Document.id == r.id).values(status="deprecated")
            )


async def _run_crawler(crawler: BaseCrawler) -> int:
    new_count = 0
    try:
        async for doc in crawler.discover():
            digest = hashlib.sha256(doc.bytes_).hexdigest()
            async with session_scope() as session:
                already = await session.scalar(
                    select(Document).where(Document.sha256 == digest)
                )
            if already is not None:
                continue
            await _supersede(doc.source_url)

            target = _bucket_dir(crawler.bucket) / (
                doc.title or f"{digest[:12]}.pdf"
            )
            target.write_bytes(doc.bytes_)
            new_count += 1
            await emit(
                "AI Regulyator",
                "downloaded",
                source=crawler.name,
                url=doc.source_url,
                bytes=len(doc.bytes_),
            )
    finally:
        await crawler.aclose()
    return new_count


class Regulyator:
    name = "AI Regulyator"

    def __init__(self) -> None:
        self._scheduler: AsyncIOScheduler | None = None

    async def crawl_once(self) -> dict[str, int]:
        await emit(self.name, "crawl.start")
        counts: dict[str, int] = {}
        for cls in (LexUzCrawler, CbuUzCrawler, IpakYuliCrawler):
            try:
                counts[cls.name] = await _run_crawler(cls())
            except Exception as e:
                await emit(self.name, "crawl.error", source=cls.name, error=str(e))
                counts[cls.name] = 0
        await emit(self.name, "crawl.done", counts=counts)
        return counts

    def schedule(self) -> None:
        if self._scheduler is not None:
            return
        s = get_settings()
        sched = AsyncIOScheduler(timezone="UTC")
        sched.add_job(self.crawl_once, CronTrigger.from_crontab(s.crawl_cron))
        sched.start()
        self._scheduler = sched

    def shutdown(self) -> None:
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None


regulyator = Regulyator()
