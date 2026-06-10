"""Tests for the LLM-driven intent classifier + its rule-based fallback."""

from __future__ import annotations

import os

os.environ.setdefault("AIM_ROOT", "/tmp/aim-root-intent-test")

import pytest

from app.agents import intent
from app.agents.intent import IntentDecision, _parse, _rule_based, detect_intent


# ── Rule-based ───────────────────────────────────────────────────────────


def test_rules_always_include_searcher() -> None:
    d = _rule_based("salom")
    assert "AI Searcher" in d.agents
    assert d.source == "rules"


def test_rules_pull_metodist_on_uzbek_compliance() -> None:
    d = _rule_based("Kredit siyosatimiz CBU sirkulyariga muvofiqmi?")
    assert "AI Metodist" in d.agents
    assert d.case_type == "normative_audit"


def test_rules_pull_shadow_on_internal() -> None:
    d = _rule_based("ichki maxfiy lotus hujjatini ko'rsat")
    assert "AI Shadow" in d.agents


def test_rules_product_check_case_type() -> None:
    d = _rule_based("yangi produkt biznes talab normativlarga muvofiqmi")
    assert d.case_type == "product_check"
    assert "AI Metodist" in d.agents


def test_rules_plain_query_is_general() -> None:
    d = _rule_based("eng yaqin filial qayerda")
    assert d.case_type == "general"
    assert d.agents == {"AI Searcher"}


# ── JSON parsing ─────────────────────────────────────────────────────────


def test_parse_clean() -> None:
    d = _parse('{"agents":["AI Searcher","AI Metodist"],"case_type":"normative_audit"}')
    assert d is not None
    assert d.agents == {"AI Searcher", "AI Metodist"}
    assert d.case_type == "normative_audit"
    assert d.source == "llm"


def test_parse_forces_searcher_and_filters_unknown_agents() -> None:
    d = _parse('{"agents":["AI Metodist","AI Bogus"],"case_type":"general"}')
    assert d is not None
    assert "AI Searcher" in d.agents       # always added
    assert "AI Metodist" in d.agents
    assert "AI Bogus" not in d.agents      # filtered


def test_parse_unknown_case_type_defaults_general() -> None:
    d = _parse('{"agents":["AI Searcher"],"case_type":"nonsense"}')
    assert d is not None
    assert d.case_type == "general"


def test_parse_strips_fences() -> None:
    d = _parse('```json\n{"agents":["AI Searcher"],"case_type":"general"}\n```')
    assert d is not None
    assert d.agents == {"AI Searcher"}


def test_parse_malformed_returns_none() -> None:
    assert _parse("not json") is None
    assert _parse('{"no_agents":true}') is None


# ── detect_intent fallback behaviour ─────────────────────────────────────


class _DemoSettings:
    aim_demo = True
    aim_llm_intent = True
    ollama_model_router = "qwen2.5:7b-instruct"


class _RealSettings:
    aim_demo = False
    aim_llm_intent = True
    ollama_model_router = "qwen2.5:7b-instruct"


@pytest.mark.asyncio
async def test_detect_intent_demo_uses_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(intent, "get_settings", lambda: _DemoSettings())
    d = await detect_intent("policy compliance check")
    assert d.source == "rules"
    assert "AI Metodist" in d.agents


@pytest.mark.asyncio
async def test_detect_intent_allow_llm_false_uses_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(intent, "get_settings", lambda: _RealSettings())
    d = await detect_intent("muvofiqmi?", allow_llm=False)
    assert d.source == "rules"


@pytest.mark.asyncio
async def test_detect_intent_uses_llm_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(intent, "get_settings", lambda: _RealSettings())

    class _FakeOllama:
        async def generate(self, *a, **k) -> str:
            return '{"agents":["AI Searcher","AI Shadow"],"case_type":"general"}'

    monkeypatch.setattr(intent, "get_ollama", lambda: _FakeOllama())
    d = await detect_intent("ichki hujjat")
    assert d.source == "llm"
    assert d.agents == {"AI Searcher", "AI Shadow"}


@pytest.mark.asyncio
async def test_detect_intent_falls_back_on_llm_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(intent, "get_settings", lambda: _RealSettings())

    class _BoomOllama:
        async def generate(self, *a, **k) -> str:
            raise ConnectionError("ollama down")

    monkeypatch.setattr(intent, "get_ollama", lambda: _BoomOllama())
    d = await detect_intent("Kredit siyosati muvofiqmi?")
    assert d.source == "rules"            # degraded gracefully
    assert "AI Metodist" in d.agents      # rules still classified it


@pytest.mark.asyncio
async def test_detect_intent_falls_back_on_bad_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(intent, "get_settings", lambda: _RealSettings())

    class _GarbageOllama:
        async def generate(self, *a, **k) -> str:
            return "I think you should run Searcher and Metodist."

    monkeypatch.setattr(intent, "get_ollama", lambda: _GarbageOllama())
    d = await detect_intent("policy gap")
    assert d.source == "rules"


@pytest.mark.asyncio
async def test_detect_intent_disabled_flag_uses_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Off:
        aim_demo = False
        aim_llm_intent = False
        ollama_model_router = "x"

    monkeypatch.setattr(intent, "get_settings", lambda: _Off())
    d = await detect_intent("compliance")
    assert d.source == "rules"
