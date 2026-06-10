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
        # truncate=True lets Ollama clip any input that overflows the model's
        # context (bge-m3 is 8192 tokens) instead of failing the whole batch
        # with HTTP 400 "input length exceeds the context length". Cyrillic /
        # Uzbek legal text tokenises densely, so a long query or attachment
        # prefix can exceed the window even after chunking.
        r = await self._client.post(
            "/api/embed",
            json={"model": model, "input": inputs, "truncate": True},
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
