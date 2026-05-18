"""Outbound HTTP whitelist.

Provides an `httpx.AsyncBaseTransport` wrapper that refuses any request
whose host is not in the allow-list. Used by the Regulyator's per-crawler
clients; the rest of the application is expected to call only loopback
services (Ollama, Postgres, Redis), which are reached over local TCP and
never via this transport.
"""

from __future__ import annotations

from collections.abc import Iterable

import httpx


class HostNotAllowed(PermissionError):
    pass


class WhitelistTransport(httpx.AsyncBaseTransport):
    def __init__(self, allowed: Iterable[str], inner: httpx.AsyncBaseTransport | None = None):
        self._allowed = frozenset(allowed)
        self._inner = inner or httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        if host not in self._allowed:
            raise HostNotAllowed(f"outbound to {host!r} blocked by whitelist")
        return await self._inner.handle_async_request(request)

    async def aclose(self) -> None:
        await self._inner.aclose()


def make_client(allowed: Iterable[str], **kwargs) -> httpx.AsyncClient:
    """Return an `AsyncClient` that can only reach `allowed` hosts."""
    transport = WhitelistTransport(allowed)
    return httpx.AsyncClient(transport=transport, **kwargs)
