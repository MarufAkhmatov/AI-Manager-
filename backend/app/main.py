"""FastAPI entrypoint.

Routers and WS endpoints are added in subsequent phases. The Architect
agent owns boot/shutdown of the filesystem watcher + initial scan.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.agents.architect import architect


@asynccontextmanager
async def lifespan(app: FastAPI):
    await architect.boot()
    try:
        yield
    finally:
        await architect.shutdown()


app = FastAPI(title="AI Manager Platform", version="0.1.0", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
