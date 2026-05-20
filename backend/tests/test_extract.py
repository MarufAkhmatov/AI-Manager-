"""Tests for the structured conflict/recommendation extraction pass."""

from __future__ import annotations

import os

os.environ.setdefault("AIM_ROOT", "/tmp/aim-root-extract-test")

import pytest

from app.agents import extract
from app.agents.cases import (
    CaseAnalysis,
    ExternalBasis,
    InternalImpact,
)


# ── JSON parsing ─────────────────────────────────────────────────────────


def test_parse_clean_json() -> None:
    raw = (
        '{"conflicts":[{"internal_ref":"Credit Policy §4","external_ref":'
        '"CBU 2025/14","why":"risk weight mismatch"}],'
        '"recommendations":[{"action":"amend","target_doc":"Credit Policy",'
        '"target_clause":"4.2","suggested_text":"set risk weight to 75%"}]}'
    )
    conflicts, recs = extract._parse(raw)
    assert len(conflicts) == 1
    assert conflicts[0].internal_ref == "Credit Policy §4"
    assert conflicts[0].why == "risk weight mismatch"
    assert len(recs) == 1
    assert recs[0].action == "amend"
    assert recs[0].target_clause == "4.2"


def test_parse_strips_markdown_fences() -> None:
    raw = '```json\n{"conflicts":[],"recommendations":[{"action":"draft","suggested_text":"x"}]}\n```'
    conflicts, recs = extract._parse(raw)
    assert conflicts == []
    assert len(recs) == 1
    assert recs[0].action == "draft"


def test_parse_extracts_object_from_surrounding_prose() -> None:
    raw = 'Here is the analysis:\n{"conflicts":[],"recommendations":[]}\nHope that helps!'
    conflicts, recs = extract._parse(raw)
    assert conflicts == []
    assert recs == []


def test_parse_malformed_returns_empty() -> None:
    assert extract._parse("not json at all") == ([], [])
    assert extract._parse("") == ([], [])
    assert extract._parse("{bad json") == ([], [])


def test_parse_coerces_unknown_action_to_review() -> None:
    raw = '{"recommendations":[{"action":"obliterate","suggested_text":"do it"}]}'
    _, recs = extract._parse(raw)
    assert recs[0].action == "review"


def test_parse_drops_entries_missing_required_fields() -> None:
    raw = (
        '{"conflicts":[{"internal_ref":"a","external_ref":"b"}],'  # no "why"
        '"recommendations":[{"action":"amend"}]}'  # no suggested_text
    )
    conflicts, recs = extract._parse(raw)
    assert conflicts == []
    assert recs == []


# ── Demo extraction ──────────────────────────────────────────────────────


def _case_with_content() -> CaseAnalysis:
    return CaseAnalysis(
        summary="Demo summary",
        affected_internal=[
            InternalImpact(
                document_id="d1",
                title="Credit Policy",
                snippet="loan classification",
                score=0.9,
                section="4.2",
                department="Credit",
            ),
            InternalImpact(
                document_id="d2",
                title="Risk Framework",
                snippet="limits",
                score=0.8,
                section=None,
                department="Risk",
            ),
        ],
        external_basis=[
            ExternalBasis(
                authority="cbu.uz",
                source_url="https://cbu.uz/c/1",
                title="Циркуляр 2025/14",
                snippet="capital adequacy",
            )
        ],
    )


def test_demo_extract_produces_conflicts_and_recs() -> None:
    case = _case_with_content()
    conflicts, recs = extract._demo_extract(case, "tahlil qiling")
    # One conflict per external act (1 here), capped at 3.
    assert len(conflicts) == 1
    assert conflicts[0].external_ref == "Циркуляр 2025/14"
    assert conflicts[0].internal_ref == "Credit Policy"
    # One recommendation per affected internal doc (2 here).
    assert len(recs) == 2
    assert {r.action for r in recs} == {"amend"}
    assert recs[0].target_doc == "Credit Policy"
    assert recs[0].target_clause == "4.2"


# ── enrich_case_analysis ─────────────────────────────────────────────────


class _FakeSettings:
    aim_demo = True
    ollama_model_router = "qwen2.5:7b-instruct"


@pytest.mark.asyncio
async def test_enrich_demo_fills_lists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(extract, "get_settings", lambda: _FakeSettings())
    case = _case_with_content()
    out = await extract.enrich_case_analysis(case, query="tahlil qiling")
    assert out is case  # mutates in place
    assert len(out.conflicts) >= 1
    assert len(out.recommendations) >= 1


@pytest.mark.asyncio
async def test_enrich_skips_when_nothing_to_compare(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(extract, "get_settings", lambda: _FakeSettings())
    empty = CaseAnalysis(summary="just a summary")
    out = await extract.enrich_case_analysis(empty, query="hi")
    assert out.conflicts == []
    assert out.recommendations == []


@pytest.mark.asyncio
async def test_enrich_noop_when_already_populated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(extract, "get_settings", lambda: _FakeSettings())
    case = _case_with_content()
    case.conflicts = [extract.Conflict(internal_ref="x", external_ref="y", why="z")]
    out = await extract.enrich_case_analysis(case, query="q")
    # Already had conflicts → left untouched, no demo override.
    assert len(out.conflicts) == 1
    assert out.conflicts[0].why == "z"
