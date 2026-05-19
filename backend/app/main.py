"""FastAPI entrypoint."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.architect import architect
from app.agents.regulyator import regulyator
from app.api import routes_agents, routes_auth, routes_chat, routes_kb, ws_hub
from app.config import get_settings
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
    settings = get_settings()
    if not settings.aim_demo:
        await architect.boot()
        asyncio.create_task(_prewarm_metodist())
        regulyator.schedule()
    try:
        yield
    finally:
        if not settings.aim_demo:
            regulyator.shutdown()
            await architect.shutdown()


app = FastAPI(title="AI Manager Platform", version="0.1.0", lifespan=lifespan)

# CORS — the Next.js dev server runs on a different origin (3000) from the
# FastAPI server (8000). Without this every fetch from the browser fails
# with a CORS preflight error. The list mirrors the dev / Docker dashboards;
# operators behind a reverse proxy who serve both on the same origin can
# safely leave this in place (same-origin requests aren't subject to CORS).
_DEFAULT_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_DEFAULT_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(routes_auth.router)
app.include_router(routes_chat.router)
app.include_router(routes_kb.router)
app.include_router(routes_agents.router)
app.include_router(ws_hub.router)
