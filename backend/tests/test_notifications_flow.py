"""Tests for Phase 4 — auto-audit + notifications feed.

Patches the Manager registry with stub agents so the audit runs without
Postgres / Ollama, then exercises the audit runner + the
/api/notifications endpoints end to end.
"""

from __future__ import annotations

import importlib
import os
import uuid

os.environ.setdefault("AIM_ROOT", "/tmp/aim-root-notif-test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.makedirs(os.environ["AIM_ROOT"], exist_ok=True)

import pytest
from fastapi.testclient import TestClient

from app.agents import manager as manager_mod
from app.agents.base import Agent, AgentContext, AgentResult, Citation
from app.security.jwt import issue_token


class _StubSearcher(Agent):
    name = "AI Searcher"

    async def run(self, ctx: AgentContext) -> AgentResult:
        return AgentResult(
            agent=self.name,
            payload={"matches": [{"snippet": "internal hit", "score": 0.9}]},
            citations=[
                Citation(
                    document_id="d1",
                    title=r"KB\Raw\Credit\policy.pdf",
                    snippet="Credit clause",
                    score=0.9,
                )
            ],
            confidence=0.9,
        )


class _StubMetodist(Agent):
    name = "AI Metodist"

    async def run(self, ctx: AgentContext) -> AgentResult:
        return AgentResult(
            agent=self.name,
            payload={
                "mode": "compare",
                "text": "Audit summary: internal credit policy needs an update.",
                "external_chunks": [
                    {
                        "source_url": "https://cbu.uz/c/1",
                        "document_number": "CBU 2025/14",
                        "authority": "cbu.uz",
                        "text": "capital adequacy clause",
                    }
                ],
            },
            citations=[],
            confidence=0.7,
        )


@pytest.fixture
def app_with_stubs(monkeypatch: pytest.MonkeyPatch):
    # Force demo so the extract pass produces deterministic conflicts/recs
    # and login accepts admin without a DB.
    monkeypatch.setenv("AIM_DEMO", "1")
    from app.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]

    monkeypatch.setattr(
        manager_mod,
        "_registry",
        lambda: {"AI Searcher": _StubSearcher(), "AI Metodist": _StubMetodist()},
    )

    from app import main as main_mod

    # Don't auto-seed demo notifications in the test — we drive them.
    async def _noop_seed() -> None: pass
    monkeypatch.setattr(main_mod, "_seed_demo_notifications", _noop_seed)

    # Reset the in-memory store between tests.
    from app import notifications as notif_mod
    notif_mod.store._items.clear()

    importlib.reload(main_mod)
    yield TestClient(main_mod.app)

    # Drop the demo-mode settings from the lru_cache so later test modules
    # see their own (non-demo) configuration.
    get_settings.cache_clear()  # type: ignore[attr-defined]
    notif_mod.store._items.clear()


def _admin() -> dict[str, str]:
    token = issue_token(
        user_id=uuid.uuid4(), username="admin", role="admin"
    )
    return {"Authorization": f"Bearer {token}"}


def _analyst() -> dict[str, str]:
    token = issue_token(
        user_id=uuid.uuid4(), username="a", role="analyst"
    )
    return {"Authorization": f"Bearer {token}"}


def test_notifications_empty_initially(app_with_stubs) -> None:
    client = app_with_stubs
    r = client.get("/api/notifications", headers=_analyst())
    assert r.status_code == 200
    body = r.json()
    assert body["unread"] == 0
    assert body["items"] == []


def test_manual_audit_creates_notification(app_with_stubs) -> None:
    client = app_with_stubs
    r = client.post(
        "/api/notifications/audit",
        headers=_admin(),
        json={
            "title": "CBU Циркуляр №2025/14",
            "text": "Yangi kapital yetarliligi normativi.",
            "source_url": "https://cbu.uz/c/2025-14",
        },
    )
    assert r.status_code == 200, r.text
    nid = r.json()["notification_id"]
    assert nid

    # It now shows up in the feed, unread.
    r2 = client.get("/api/notifications", headers=_analyst())
    body = r2.json()
    assert body["unread"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["id"] == nid
    assert item["kind"] == "audit"
    assert item["title"] == "CBU Циркуляр №2025/14"
    assert item["read"] is False
    # The audit ran the full comparison → case_analysis is populated.
    ca = item["case_analysis"]
    assert "summary" in ca
    assert isinstance(ca["recommendations"], list)
    # Demo extraction fills recommendations from the internal hit.
    assert len(ca["recommendations"]) >= 1


def test_audit_requires_admin(app_with_stubs) -> None:
    client = app_with_stubs
    r = client.post(
        "/api/notifications/audit",
        headers=_analyst(),
        json={"title": "x", "text": "y"},
    )
    assert r.status_code == 403


def test_mark_read_flips_unread_count(app_with_stubs) -> None:
    client = app_with_stubs
    client.post(
        "/api/notifications/audit",
        headers=_admin(),
        json={"title": "Act A", "text": "body"},
    )
    nid = client.get("/api/notifications", headers=_analyst()).json()["items"][0]["id"]

    r = client.post(f"/api/notifications/{nid}/read", headers=_analyst())
    assert r.status_code == 204

    body = client.get("/api/notifications", headers=_analyst()).json()
    assert body["unread"] == 0
    assert body["items"][0]["read"] is True


def test_mark_read_unknown_is_404(app_with_stubs) -> None:
    client = app_with_stubs
    r = client.post("/api/notifications/does-not-exist/read", headers=_analyst())
    assert r.status_code == 404


def test_read_all(app_with_stubs) -> None:
    client = app_with_stubs
    for i in range(3):
        client.post(
            "/api/notifications/audit",
            headers=_admin(),
            json={"title": f"Act {i}", "text": "body"},
        )
    assert client.get("/api/notifications", headers=_analyst()).json()["unread"] == 3
    r = client.post("/api/notifications/read-all", headers=_analyst())
    assert r.json()["marked"] == 3
    assert client.get("/api/notifications", headers=_analyst()).json()["unread"] == 0
