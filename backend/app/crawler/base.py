"""Base for Regulyator crawlers.

Each concrete crawler subclasses `BaseCrawler`, declares its `allowed_host`,
and implements `discover()` returning `CrawledDoc` items. The HTTP client
enforces the outbound whitelist — attempts to reach any host other than
the declared one raise immediately. Phase 7 wires this whitelist for the
whole Regulyator process at the transport layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import date

import httpx

from app.config import get_settings


@dataclass(slots=True)
class CrawledDoc:
    source_url: str
    title: str | None
    issued_at: date | None
    content_type: str
    bytes_: bytes


class BaseCrawler(ABC):
    name: str
    bucket: str
    allowed_host: str

    def __init__(self) -> None:
        s = get_settings()
        if self.allowed_host not in s.allowed_hosts:
            raise RuntimeError(
                f"{self.name}: host {self.allowed_host!r} not in CRAWL_ALLOWED_HOSTS"
            )
        self._client = httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": "ai-manager-platform/0.1 (+local)"},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get(self, url: str) -> httpx.Response:
        host = httpx.URL(url).host
        if host != self.allowed_host:
            raise PermissionError(f"crawler {self.name}: refused host {host!r}")
        return await self._client.get(url)

    @abstractmethod
    def discover(self) -> AsyncIterator[CrawledDoc]:
        """Yield candidate documents to ingest. Implementations are async generators."""
        raise NotImplementedError
