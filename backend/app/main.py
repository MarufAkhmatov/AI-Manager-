"""FastAPI entrypoint."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.architect import architect
from app.agents.regulyator import regulyator
from app.api import (
    routes_agents,
    routes_attachments,
    routes_auth,
    routes_chat,
    routes_kb,
    routes_notifications,
    ws_hub,
)
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


async def _seed_demo_notifications() -> None:
    """Demo mode: there's no real crawl, so seed a couple of auto-audit
    findings at boot. Gives the operator a populated bell to click through
    without waiting for the daily Regulyator schedule."""
    from app.agents.audit import audit_document

    await audit_document(
        title="CBU Циркуляр №2025/14 — kapital yetarliligi (demo)",
        text=(
            "Markaziy bankning yangi sirkulyari kredit risklari hisobi va "
            "kapital yetarliligi normativlarini o'zgartirdi. Ipoteka "
            "kreditlari uchun risk koeffitsiyenti 75% etib belgilandi."
        ),
        source_url="https://cbu.uz/circulars/2025-14",
    )
    await audit_document(
        title="ЎзР Қонуни 250-сон — banklar faoliyati (demo)",
        text=(
            "Banklar faoliyati to'g'risidagi qonunga o'zgartishlar: "
            "iste'mol kreditlari bo'yicha maksimal yillik foiz stavkasi "
            "cheklandi va mijozni identifikatsiya qilish talablari kuchaytirildi."
        ),
        source_url="https://lex.uz/docs/demo-250",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if not settings.aim_demo:
        # Restore persisted auto-audit findings so the bell isn't empty
        # after a restart.
        try:
            from app.notifications import load_from_db

            await load_from_db()
        except Exception:
            pass
        await architect.boot()
        asyncio.create_task(_prewarm_metodist())
        regulyator.schedule()
    else:
        # Populate the notifications bell so the Phase-4 flow is visible
        # without a real crawl + ingestion cycle.
        asyncio.create_task(_seed_demo_notifications())
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
app.include_router(routes_attachments.router)
app.include_router(routes_kb.router)
app.include_router(routes_agents.router)
app.include_router(routes_notifications.router)
app.include_router(ws_hub.router)
