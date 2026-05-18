"""Thin async client for the local Ollama server (no external network)."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings


class OllamaClient:
    def __init__(self, host: str | None = None) -> None:
        s = get_settings()
        self.host = host or s.ollama_host
        self._client = httpx.AsyncClient(base_url=self.host, timeout=60)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def generate(
        self,
        model: str,
        prompt: str,
        *,
        system: str | None = None,
        options: dict[str, Any] | None = None,
        stream: bool = False,
    ) -> str:
        payload: dict[str, Any] = {"model": model, "prompt": prompt, "stream": stream}
        if system:
            payload["system"] = system
        if options:
            payload["options"] = options
        r = await self._client.post("/api/generate", json=payload)
        r.raise_for_status()
        data = r.json()
        return data.get("response", "")

    async def embed(self, model: str, inputs: list[str]) -> list[list[float]]:
        r = await self._client.post(
            "/api/embed",
            json={"model": model, "input": inputs},
        )
        r.raise_for_status()
        data = r.json()
        return data["embeddings"]


_client: OllamaClient | None = None


def get_ollama() -> OllamaClient:
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client
