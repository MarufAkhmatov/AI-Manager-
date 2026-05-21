"""LLM backend selector.

`get_llm()` returns whichever generative client the deployment is configured
for (`AIM_LLM_BACKEND`): the local Ollama server (default) or Claude via the
Anthropic API. Both expose the same `generate(model, prompt, system=...,
options=...)` coroutine, so agent call sites are backend-agnostic.

Embeddings are NOT routed here — they stay on the local bge-m3 model
(`app/llm/embeddings.py`), which is fast even on CPU.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.config import get_settings
from app.llm.ollama_client import get_ollama

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.llm.anthropic_client import AnthropicClient

_anthropic: "AnthropicClient | None" = None


def get_llm():  # noqa: ANN201 - returns a structurally-typed generate() client
    """Return the configured generative LLM client (Ollama or Anthropic)."""
    s = get_settings()
    if getattr(s, "aim_llm_backend", "ollama").lower() == "anthropic":
        global _anthropic
        if _anthropic is None:
            from app.llm.anthropic_client import AnthropicClient

            _anthropic = AnthropicClient()
        return _anthropic
    return get_ollama()
