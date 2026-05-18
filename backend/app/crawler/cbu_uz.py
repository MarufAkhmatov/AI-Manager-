"""cbu.uz crawler — Central Bank of Uzbekistan."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from datetime import date

from app.crawler.base import BaseCrawler, CrawledDoc

_PDF_LINK = re.compile(r'href="([^"]+\.pdf)"', re.IGNORECASE)


class CbuUzCrawler(BaseCrawler):
    name = "cbu.uz"
    bucket = "cbu_uz"
    allowed_host = "cbu.uz"

    async def discover(self) -> AsyncIterator[CrawledDoc]:  # type: ignore[override]
        index_url = "https://cbu.uz/ru/press_center/news/"
        try:
            r = await self._get(index_url)
        except Exception:
            return
        for match in _PDF_LINK.finditer(r.text):
            url = match.group(1)
            if url.startswith("//"):
                url = "https:" + url
            elif url.startswith("/"):
                url = f"https://{self.allowed_host}{url}"
            try:
                doc = await self._get(url)
            except Exception:
                continue
            yield CrawledDoc(
                source_url=url,
                title=url.rsplit("/", 1)[-1],
                issued_at=date.today(),
                content_type=doc.headers.get("content-type", "application/pdf"),
                bytes_=doc.content,
            )
