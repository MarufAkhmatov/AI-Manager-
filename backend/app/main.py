"""FastAPI entrypoint. Routers, agents, and pipeline land in Phase 1+."""

from fastapi import FastAPI

app = FastAPI(title="AI Manager Platform", version="0.1.0")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
