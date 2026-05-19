"""End-to-end tests for the attachment upload + chat flow (Case 1).

Upload a small TXT file → POST /api/chat with the returned id →
verify Manager folds the OCR'd text into the query, Metodist is
included even on a terse user message, and the response's
``attachment`` metadata round-trips back to the client.
"""

from __future__ import annotations

import io
import os

os.environ.setdefault("AIM_ROOT", "/tmp/aim-root-attach-test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.makedirs(os.environ["AIM_ROOT"], exist_ok=True)

import importlib
import uuid

import pytest
from fastapi.testclient import TestClient

from app.agents import manager as manager_mod
from app.agents.base import Agent, AgentContext, AgentResult, Citation
from app.security.jwt import issue_token


class _RecordingSearcher(Agent):
    """Stub Searcher that captures the effective query Manager sent."""

    name = "AI Searcher"

    def __init__(self) -> None:
        self.last_query: str | None = None

    async def run(self, ctx: AgentContext) -> AgentResult:
        self.last_query = ctx.query
        return AgentResult(
            agent=self.name,
            payload={
                "matches": [
                    {
                        "snippet": "stub hit",
                        "score": 0.9,
                        "title": r"KB\Raw\Credit\policy.pdf",
                    }
                ]
            },
            citations=[
                Citation(
                    document_id="d1",
                    title=r"KB\Raw\Credit\policy.pdf",
                    snippet="Credit policy stub",
                    score=0.9,
                )
            ],
            confidence=0.9,
        )


class _RecordingMetodist(Agent):
    name = "AI Metodist"

    def __init__(self) -> None:
        self.called = False
        self.last_query: str | None = None

    async def run(self, ctx: AgentContext) -> AgentResult:
        self.called = True
        self.last_query = ctx.query
        return AgentResult(
            agent=self.name,
            payload={"mode": "compare", "text": "stub metodist analysis"},
            citations=[],
            confidence=0.7,
        )


@pytest.fixture
def app_with_stubs(monkeypatch: pytest.MonkeyPatch):
    searcher_stub = _RecordingSearcher()
    metodist_stub = _RecordingMetodist()
    monkeypatch.setattr(
        manager_mod,
        "_registry",
        lambda: {
            "AI Searcher": searcher_stub,
            "AI Metodist": metodist_stub,
        },
    )

    from app.agents import architect as arch_mod
    from app.agents import regulyator as reg_mod

    class _N:
        async def boot(self) -> None: pass
        async def shutdown(self) -> None: pass

    class _NR:
        def schedule(self) -> None: pass
        def shutdown(self) -> None: pass

    monkeypatch.setattr(arch_mod, "architect", _N())
    monkeypatch.setattr(reg_mod, "regulyator", _NR())

    from app import main as main_mod

    async def _noop() -> None: pass
    monkeypatch.setattr(main_mod, "_prewarm_metodist", _noop)
    importlib.reload(main_mod)
    client = TestClient(main_mod.app)
    return client, {"searcher": searcher_stub, "metodist": metodist_stub}


def _bearer() -> dict[str, str]:
    token = issue_token(user_id=uuid.uuid4(), username="tester", role="analyst")
    return {"Authorization": f"Bearer {token}"}


def test_upload_requires_token(app_with_stubs) -> None:
    client, _ = app_with_stubs
    r = client.post(
        "/api/chat/attachments",
        files={"file": ("letter.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert r.status_code == 401


def test_upload_rejects_unknown_extension(app_with_stubs) -> None:
    client, _ = app_with_stubs
    r = client.post(
        "/api/chat/attachments",
        headers=_bearer(),
        files={"file": ("evil.exe", io.BytesIO(b"MZ\x00\x00"), "application/octet-stream")},
    )
    assert r.status_code == 415


def test_upload_then_chat_folds_text_into_query(app_with_stubs) -> None:
    client, stubs = app_with_stubs

    letter = (
        "Hurmatli rahbar,\n\n"
        "Markaziy bankning yangi sirkulyari N 2025/14 ga ko'ra "
        "kredit risklari hisobi qoidalari o'zgartirildi. "
        "Ichki normativlarni qayta ko'rib chiqishingizni so'raymiz."
    ).encode()

    r = client.post(
        "/api/chat/attachments",
        headers=_bearer(),
        files={"file": ("circular-2025-14.txt", io.BytesIO(letter), "text/plain")},
    )
    assert r.status_code == 200, r.text
    up = r.json()
    assert up["filename"] == "circular-2025-14.txt"
    assert up["char_count"] == len(letter.decode())
    assert "Markaziy" in up["preview"]
    attachment_id = up["attachment_id"]

    # Now send a terse user message — Manager should still pull Metodist
    # in because the attachment carries comparison intent.
    r2 = client.post(
        "/api/chat",
        headers=_bearer(),
        json={"message": "tahlil qiling", "attachment_id": attachment_id},
    )
    assert r2.status_code == 200, r2.text
    body = r2.json()

    # The attachment metadata is echoed back.
    assert body["attachment"]["id"] == attachment_id
    assert body["attachment"]["filename"] == "circular-2025-14.txt"

    # Manager-side: both stubs received an effective query containing both
    # the user message and the attachment body.
    eff = stubs["searcher"].last_query
    assert "tahlil qiling" in eff
    assert "Markaziy bankning yangi sirkulyari" in eff
    assert "circular-2025-14.txt" in eff

    # Metodist ran even though the user message itself had no compliance
    # keywords — the upload-mode override added it to the plan.
    assert stubs["metodist"].called is True
    assert "AI Metodist" in body["agents_used"]
    assert body["agents_used"][-1] == "AI Secure"


def test_chat_with_missing_attachment_falls_back_to_message(app_with_stubs) -> None:
    client, stubs = app_with_stubs
    # Use a random id that was never uploaded.
    r = client.post(
        "/api/chat",
        headers=_bearer(),
        json={
            "message": "is this internal policy compliant?",
            "attachment_id": "deadbeef00000000",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Manager surfaces the missing attachment so the UI can flag it.
    assert body["attachment"]["missing"] is True
    # And the user's typed message still drove the search.
    assert "is this internal policy compliant" in stubs["searcher"].last_query
