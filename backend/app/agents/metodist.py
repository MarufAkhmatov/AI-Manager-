"""AI Metodist — thin wrapper around the standalone `metodist-agent` package.

The standalone lives at `settings.metodist_standalone_path` (default
`{AIM_ROOT}/KB/AI Metodist Agent/`). It is a self-contained PEP 621 package
with its own hybrid retrieval (BM25 + BGE-M3 over the bank methodology
PDFs) and its own Anthropic client. The operator activates it with:

    pip install -e "C:\\Users\\ASUS\\Desktop\\AI Manager\\KB\\AI Metodist Agent"

This wrapper:

  * Lazily imports `metodist_agent.agent.Agent` on first call so the platform
    can boot even when the standalone isn't installed yet.
  * Loads the standalone's own `.env` (which holds `ANTHROPIC_API_KEY`)
    before the import — without forcing operators to duplicate the key in
    the platform `.env`.
  * Caches a single standalone `Agent()` per process (model load + index
    build is ~30 s; subsequent calls are dominated by the Claude API
    round-trip).
  * Calls `ask()` by default; switches to `compare()` when the query reads
    like a compliance / divergence check. Both are sync, so we hop to a
    thread via `asyncio.to_thread`.
  * Does NOT use AI Searcher. The standalone has its own retriever over
    its own BGE-M3 index — running both would mean two searches and
    potentially conflicting results.
  * Does NOT spawn the standalone's watcher or crawler. AI Architect
    already watches `AIM_ROOT`; AI Regulyator already crawls the
    whitelisted hosts. The wrapper only instantiates `Agent()` (which
    performs no I/O beyond loading cached embeddings) and calls
    `ask`/`compare` (which never touch the network for retrieval).
"""

from __future__ import annotations

import asyncio
import os
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.agents.base import Agent, AgentContext, AgentResult, Citation
from app.config import get_settings
from app.events import emit

if TYPE_CHECKING:  # pragma: no cover - typing only
    from metodist_agent.agent import Agent as StandaloneAgent
    from metodist_agent.chunk import Chunk as StandaloneChunk


_COMPARE_KEYWORDS: tuple[str, ...] = (
    "compare", "comparison", "compliance", "diff", "divergence", "discrepancy",
    "сравни", "сравнение", "соответств", "расхожден", "противореч", "нарушени",
    "qiyosla", "muvofiq", "farq",
)


def _pick_mode(query: str) -> str:
    q = query.lower()
    return "compare" if any(k in q for k in _COMPARE_KEYWORDS) else "ask"


def _load_standalone_env(standalone_path: Path) -> None:
    """Hydrate ANTHROPIC_API_KEY (and anything else in the standalone's .env)
    into os.environ if not already set. We never override an existing var
    so the platform .env still wins when both define the same key."""
    env_file = standalone_path / ".env"
    if not env_file.is_file():
        return
    try:
        for raw in env_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
    except OSError:
        pass  # best-effort; standalone will raise a clear error on first call


_agent_lock = threading.Lock()
_agent: "StandaloneAgent | None" = None
_agent_import_error: Exception | None = None


def _get_or_init_agent() -> "StandaloneAgent":
    """Singleton init for the heavyweight standalone Agent.

    First call: loads BGE-M3 weights (~2.3 GB RAM) and the hybrid retriever
    over `.cache/embeddings/matrix.npy`. Subsequent calls are free.
    Raises if `metodist_agent` is not importable.
    """
    global _agent, _agent_import_error
    if _agent is not None:
        return _agent
    with _agent_lock:
        if _agent is not None:
            return _agent
        if _agent_import_error is not None:
            raise _agent_import_error
        try:
            _load_standalone_env(get_settings().metodist_standalone_path)
            from metodist_agent.agent import Agent as StandaloneAgent  # noqa: WPS433
            _agent = StandaloneAgent()
            return _agent
        except Exception as e:  # ImportError, FileNotFoundError, anthropic.AuthError, ...
            _agent_import_error = e
            raise


def _internal_citation(c: "StandaloneChunk") -> Citation:
    """Convert a standalone internal Chunk to a platform Citation."""
    try:
        from metodist_agent.extract import CORPUS_ROOT  # local import; safe after init
        rel = c.source.relative_to(CORPUS_ROOT)
        title = str(rel)
    except Exception:
        title = c.source.name
    return Citation(
        document_id=title,
        title=title,
        snippet=c.text[:600],
        score=0.0,
    )


def _external_citation(c: "StandaloneChunk") -> Citation:
    """Convert a standalone external (lex.uz / cbu.uz) Chunk to Citation."""
    title_bits = [c.document_number, c.authority]
    title = " · ".join(b for b in title_bits if b) or "external act"
    return Citation(
        document_id=c.source_url,
        title=title,
        snippet=c.text[:600],
        score=0.0,
    )


def _run_ask(query: str) -> dict[str, Any]:
    agent = _get_or_init_agent()
    text, chunks = agent.ask(query)
    return {
        "mode": "ask",
        "text": text,
        "internal_chunks": chunks,
        "external_chunks": [],
    }


def _run_compare(query: str) -> dict[str, Any]:
    agent = _get_or_init_agent()
    text, internal, external = agent.compare(query)
    return {
        "mode": "compare",
        "text": text,
        "internal_chunks": internal,
        "external_chunks": external,
    }


class Metodist:
    name = "AI Metodist"

    async def run(self, ctx: AgentContext) -> AgentResult:
        start = time.perf_counter()
        mode = _pick_mode(ctx.query)
        await emit(
            self.name,
            "standalone.call",
            task_id=str(ctx.task_id),
            mode=mode,
            query=ctx.query[:200],
        )
        try:
            worker = _run_compare if mode == "compare" else _run_ask
            out = await asyncio.to_thread(worker, ctx.query)
        except Exception as e:
            await emit(
                self.name,
                "standalone.error",
                task_id=str(ctx.task_id),
                error=f"{type(e).__name__}: {e}",
            )
            return AgentResult(
                agent=self.name,
                payload={
                    "mode": mode,
                    "error": f"{type(e).__name__}: {e}",
                    "text": "",
                },
                citations=[],
                confidence=0.0,
                ms_elapsed=int((time.perf_counter() - start) * 1000),
                confidential_origin=False,
            )

        internal_chunks = out["internal_chunks"]
        external_chunks = out["external_chunks"]
        citations = [_internal_citation(c) for c in internal_chunks]
        citations.extend(_external_citation(c) for c in external_chunks)
        payload = {
            "mode": out["mode"],
            "text": out["text"],
            "internal_count": len(internal_chunks),
            "external_count": len(external_chunks),
        }
        ms = int((time.perf_counter() - start) * 1000)
        await emit(
            self.name,
            "standalone.done",
            task_id=str(ctx.task_id),
            mode=out["mode"],
            internal_count=len(internal_chunks),
            external_count=len(external_chunks),
            ms_elapsed=ms,
        )
        return AgentResult(
            agent=self.name,
            payload=payload,
            citations=citations,
            confidence=1.0 if (internal_chunks or external_chunks) else 0.0,
            ms_elapsed=ms,
            confidential_origin=False,
        )


metodist = Metodist()
