"""Integration tests for the chat flow.

We don't have Postgres / Redis / Ollama in the test env, so each test
patches the sub-agents and the Secure passthrough to in-memory stubs and
verifies:

  * `/api/chat` requires a valid bearer token (401 otherwise).
  * Manager.chat returns the masked aggregate and the agents_used list
    always ends with `AI Secure` (mandatory egress).
  * Manager.suggest skips Metodist even when the query is a normative one
    (compliance / conflict / нарушени keywords).
  * /healthz works without auth.
  * CORS preflight on /api/chat returns the expected headers so the
    Next.js dev origin can reach the backend.
"""

from __future__ import annotations

import os

os.environ.setdefault("AIM_ROOT", "/tmp/aim-root-chat-test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import uuid

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
            payload={"matches": [{"snippet": "stub hit for " + ctx.query, "score": 0.91}]},
            citations=[
                Citation(
                    document_id="doc-1",
                    title="Stub Doc 1",
                    snippet="hit for " + ctx.query,
                    score=0.91,
                )
            ],
            confidence=0.91,
            confidential_origin=False,
        )


class _StubMetodist(Agent):
    name = "AI Metodist"

    def __init__(self) -> None:
        self.called = False

    async def run(self, ctx: AgentContext) -> AgentResult:
        self.called = True
        return AgentResult(
            agent=self.name,
            payload={"mode": "compare", "text": "stub metodist answer"},
            citations=[],
            confidence=0.5,
            confidential_origin=False,
        )


@pytest.fixture
def app_with_stubs(monkeypatch: pytest.MonkeyPatch):
    """Mount the FastAPI app with all heavyweight agents and the FS lifespan
    replaced by stubs. The fixture yields (TestClient, captured stubs)."""

    searcher_stub = _StubSearcher()
    metodist_stub = _StubMetodist()

    monkeypatch.setattr(
        manager_mod, "_registry", lambda: {
            "AI Searcher": searcher_stub,
            "AI Metodist": metodist_stub,
        }
    )

    # Replace Architect / Regulyator boot so the app starts without a real DB.
    from app.agents import architect as arch_mod
    from app.agents import regulyator as reg_mod

    class _Noop:
        async def boot(self) -> None: pass
        async def shutdown(self) -> None: pass

    class _NoopReg:
        def schedule(self) -> None: pass
        def shutdown(self) -> None: pass

    monkeypatch.setattr(arch_mod, "architect", _Noop())
    monkeypatch.setattr(reg_mod, "regulyator", _NoopReg())

    # Replace the Metodist prewarm so it doesn't try to import the standalone.
    async def _noop_prewarm() -> None: pass
    from app import main as main_mod
    monkeypatch.setattr(main_mod, "_prewarm_metodist", _noop_prewarm)

    # Build a fresh app instance picking up the patched lifespan helpers.
    import importlib
    importlib.reload(main_mod)
    client = TestClient(main_mod.app)
    return client, {"searcher": searcher_stub, "metodist": metodist_stub}


def _bearer(role: str = "analyst") -> dict[str, str]:
    token = issue_token(user_id=uuid.uuid4(), username="tester", role=role)
    return {"Authorization": f"Bearer {token}"}


def test_healthz_no_auth(app_with_stubs) -> None:
    client, _ = app_with_stubs
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_chat_requires_token(app_with_stubs) -> None:
    client, _ = app_with_stubs
    r = client.post("/api/chat", json={"message": "anything"})
    assert r.status_code == 401


def test_chat_full_dag_runs_metodist_on_compliance_query(app_with_stubs) -> None:
    client, stubs = app_with_stubs
    r = client.post(
        "/api/chat",
        json={"message": "is this policy compliant with the latest CBU circular?"},
        headers=_bearer(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # AI Secure is mandatory and last.
    assert body["agents_used"][-1] == "AI Secure"
    # Metodist ran because keywords matched.
    assert stubs["metodist"].called is True
    # Aggregated payload mentions Searcher's hit.
    blob = str(body["response"])
    assert "stub hit for" in blob


def test_chat_suggest_skips_metodist(app_with_stubs) -> None:
    """suggest() uses the lighter plan — Metodist is dropped even when
    the query keywords would otherwise pull it in."""
    client, stubs = app_with_stubs
    r = client.post(
        "/api/chat/suggest",
        json={"message": "policy conflict compliance check"},
        headers=_bearer(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "AI Metodist" not in body["agents_used"]
    assert "AI Searcher" in body["agents_used"]
    assert body["agents_used"][-1] == "AI Secure"
    assert stubs["metodist"].called is False


def test_cors_allows_dashboard_origin(app_with_stubs) -> None:
    client, _ = app_with_stubs
    # Browsers send an OPTIONS preflight before non-simple cross-origin POSTs.
    r = client.options(
        "/api/chat",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type, authorization",
        },
    )
    assert r.status_code in (200, 204)
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
    allow_methods = r.headers.get("access-control-allow-methods", "")
    assert "POST" in allow_methods or allow_methods == "*"
