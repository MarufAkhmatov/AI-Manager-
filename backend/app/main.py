"""FastAPI entrypoint."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.agents.architect import architect
from app.agents.regulyator import regulyator
from app.api import routes_agents, routes_auth, routes_chat, routes_kb, ws_hub
from app.events import emit


async def _prewarm_metodist() -> None:
    """Load BGE-M3 weights and build the hybrid retriever once at boot so
    the first user-facing call doesn't pay the ~30 s cold-load on top of
    the Claude round-trip. Fire-and-forget — if the standalone isn't
    installed, surface the error on the WS bus and let the rest of the
    platform keep running."""
    try:
        from app.agents.metodist import _get_or_init_agent

        await asyncio.to_thread(_get_or_init_agent)
        await emit("AI Metodist", "prewarm.done")
    except Exception as e:
        await emit(
            "AI Metodist",
            "prewarm.error",
            error=f"{type(e).__name__}: {e}",
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await architect.boot()
    asyncio.create_task(_prewarm_metodist())
    regulyator.schedule()
    try:
        yield
    finally:
        regulyator.shutdown()
        await architect.shutdown()


app = FastAPI(title="AI Manager Platform", version="0.1.0", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(routes_auth.router)
app.include_router(routes_chat.router)
app.include_router(routes_kb.router)
app.include_router(routes_agents.router)
app.include_router(ws_hub.router)
