"""FastAPI entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.agents.architect import architect
from app.agents.regulyator import regulyator
from app.api import routes_agents, routes_auth, routes_chat, routes_kb, ws_hub


@asynccontextmanager
async def lifespan(app: FastAPI):
    await architect.boot()
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
