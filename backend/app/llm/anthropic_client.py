"""Anthropic (Claude) client exposing the same `generate()` shape as OllamaClient.

The platform's generative steps (intent routing in `agents/intent.py`, the
conflict/recommendation extraction in `agents/extract.py`) call
`get_llm().generate(model, prompt, system=..., options=...)`. On a CPU-only
host the local Ollama 7B/8B models are too slow (~minutes per call), so this
client lets those same call sites run against Claude instead — fast, and
higher quality for compliance reasoning. Selected via `AIM_LLM_BACKEND`.

The static system prompts are marked with `cache_control` so repeated calls
hit the Anthropic prompt cache instead of re-billing the prefix.
"""

from __future__ import annotations

from typing import Any

from app.config import get_settings


class AnthropicClient:
    def __init__(self) -> None:
        from anthropic import AsyncAnthropic

        s = get_settings()
        if not s.anthropic_api_key:
            raise RuntimeError(
                "AIM_LLM_BACKEND=anthropic but ANTHROPIC_API_KEY is unset"
            )
        self._client = AsyncAnthropic(api_key=s.anthropic_api_key)
        self._model = s.anthropic_model
        self._max_tokens = s.anthropic_max_tokens

    async def aclose(self) -> None:
        await self._client.close()

    async def generate(
        self,
        model: str,  # ignored — kept for OllamaClient signature parity
        prompt: str,
        *,
        system: str | None = None,
        options: dict[str, Any] | None = None,
        stream: bool = False,
    ) -> str:
        opts = options or {}
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "temperature": float(opts.get("temperature", 0.0)),
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            # Cache the static system prompt across calls.
            kwargs["system"] = [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        msg = await self._client.messages.create(**kwargs)
        return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
