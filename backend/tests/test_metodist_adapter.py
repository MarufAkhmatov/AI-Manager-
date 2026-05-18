"""Unit smoke for the AI Metodist adapter.

We can't spin up the full standalone in CI (BGE-M3 model is 2.3 GB and
the corpus is ~200 PDFs), so we stub `metodist_agent.agent.Agent` in
sys.modules before the wrapper imports it. The tests verify the wrapper
contract: mode routing, citation mapping, error handling, event emission.
"""

from __future__ import annotations

import sys
import types
import uuid
from pathlib import Path

import pytest

from app.agents.base import AgentContext
from app.agents.metodist import _pick_mode
from app.events import bus


@pytest.fixture
def fake_standalone(monkeypatch):
    """Install a stub `metodist_agent` package and reset the wrapper singleton."""
    fake_root = types.ModuleType("metodist_agent")
    fake_root.__path__ = []  # mark as a package so submodule imports work
    fake_agent_mod = types.ModuleType("metodist_agent.agent")
    fake_chunk_mod = types.ModuleType("metodist_agent.chunk")
    fake_extract_mod = types.ModuleType("metodist_agent.extract")

    class FakeChunk:
        def __init__(
            self,
            source: Path,
            page: int,
            section: str | None,
            text: str,
            *,
            source_url: str | None = None,
            document_number: str | None = None,
            authority: str | None = None,
            published_at: str | None = None,
        ) -> None:
            self.source = source
            self.page = page
            self.section = section
            self.text = text
            self.source_url = source_url
            self.document_number = document_number
            self.authority = authority
            self.published_at = published_at

    captured: dict = {"ask": [], "compare": [], "init_count": 0}

    class FakeAgent:
        def __init__(self) -> None:
            captured["init_count"] += 1

        def ask(self, q: str, k: int = 8):
            captured["ask"].append(q)
            return (
                f"ANSWER: {q}",
                [FakeChunk(Path("/fake/Dept/doc.pdf"), 3, "§1.1", "internal snippet")],
            )

        def compare(self, q: str, **kwargs):
            captured["compare"].append(q)
            return (
                f"COMPARE: {q}",
                [FakeChunk(Path("/fake/Dept/internal.pdf"), 2, "§2", "internal text")],
                [
                    FakeChunk(
                        Path("/fake/.cache/external/lex/123.json"),
                        1,
                        None,
                        "external text",
                        source_url="https://lex.uz/docs/123",
                        document_number="ЦБ 31/11",
                        authority="ЦБ РУз",
                        published_at="2025-01-01",
                    )
                ],
            )

    fake_agent_mod.Agent = FakeAgent
    fake_chunk_mod.Chunk = FakeChunk
    fake_extract_mod.CORPUS_ROOT = Path("/fake")

    monkeypatch.setitem(sys.modules, "metodist_agent", fake_root)
    monkeypatch.setitem(sys.modules, "metodist_agent.agent", fake_agent_mod)
    monkeypatch.setitem(sys.modules, "metodist_agent.chunk", fake_chunk_mod)
    monkeypatch.setitem(sys.modules, "metodist_agent.extract", fake_extract_mod)

    from app.agents import metodist as wrapper

    monkeypatch.setattr(wrapper, "_agent", None, raising=False)
    monkeypatch.setattr(wrapper, "_agent_import_error", None, raising=False)
    return captured


def _ctx(query: str) -> AgentContext:
    return AgentContext(task_id=uuid.uuid4(), user_id=None, role="staff", query=query)


def test_pick_mode_routes_compliance_to_compare() -> None:
    assert _pick_mode("Что говорится о ставке?") == "ask"
    assert _pick_mode("Compare internal policy with CBU act") == "compare"
    assert _pick_mode("есть ли расхождения по LTV?") == "compare"
    assert _pick_mode("muvofiq ekanligini tekshir") == "compare"


async def test_ask_path_returns_internal_citations(fake_standalone) -> None:
    from app.agents.metodist import metodist

    result = await metodist.run(_ctx("какая ставка по вкладу"))

    assert result.agent == "AI Metodist"
    assert result.payload["mode"] == "ask"
    assert result.payload["text"].startswith("ANSWER:")
    assert result.payload["internal_count"] == 1
    assert result.payload["external_count"] == 0
    assert len(result.citations) == 1
    assert result.citations[0].title.endswith("doc.pdf")
    assert result.confidential_origin is False
    assert result.confidence == 1.0
    assert fake_standalone["ask"] and not fake_standalone["compare"]


async def test_compare_path_returns_both_citations(fake_standalone) -> None:
    from app.agents.metodist import metodist

    result = await metodist.run(_ctx("проверь соответствие с актами ЦБ"))

    assert result.payload["mode"] == "compare"
    assert result.payload["internal_count"] == 1
    assert result.payload["external_count"] == 1
    assert len(result.citations) == 2
    ext = next(c for c in result.citations if c.document_id == "https://lex.uz/docs/123")
    assert "ЦБ 31/11" in ext.title
    assert fake_standalone["compare"] and not fake_standalone["ask"]


async def test_singleton_initialises_standalone_once(fake_standalone) -> None:
    from app.agents.metodist import metodist

    await metodist.run(_ctx("ставка по депозиту"))
    await metodist.run(_ctx("срок рассмотрения"))
    await metodist.run(_ctx("сравни с лимитом ЦБ"))
    assert fake_standalone["init_count"] == 1


async def test_emits_standalone_call_and_done(fake_standalone) -> None:
    from app.agents.metodist import metodist

    async with bus.subscribe() as q:
        await metodist.run(_ctx("какая ставка"))
        events = []
        for _ in range(2):
            events.append(await q.get())

    names = [(e.agent, e.event) for e in events]
    assert ("AI Metodist", "standalone.call") in names
    assert ("AI Metodist", "standalone.done") in names


async def test_standalone_error_returns_clean_agent_result(monkeypatch) -> None:
    """When the standalone raises (e.g. not installed), the wrapper returns
    an empty AgentResult rather than crashing the manager."""
    fake_root = types.ModuleType("metodist_agent")
    fake_root.__path__ = []
    fake_agent_mod = types.ModuleType("metodist_agent.agent")

    class BoomAgent:
        def __init__(self) -> None:
            raise RuntimeError("BGE-M3 weights not found")

    fake_agent_mod.Agent = BoomAgent
    monkeypatch.setitem(sys.modules, "metodist_agent", fake_root)
    monkeypatch.setitem(sys.modules, "metodist_agent.agent", fake_agent_mod)

    from app.agents import metodist as wrapper

    monkeypatch.setattr(wrapper, "_agent", None, raising=False)
    monkeypatch.setattr(wrapper, "_agent_import_error", None, raising=False)

    result = await wrapper.metodist.run(_ctx("anything"))
    assert result.payload["error"].startswith("RuntimeError:")
    assert result.confidence == 0.0
    assert result.citations == []
