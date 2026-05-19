"""Tests for the CaseAnalysis builder — the structured projection we
ship next to /api/chat's raw response so the Recommendation panel can
render impact / sources / departments without re-parsing free text.
"""

from __future__ import annotations

import os

os.environ.setdefault("AIM_ROOT", "/tmp/aim-root-cases-test")

from app.agents.base import AgentResult, Citation  # noqa: E402
from app.agents.cases import (  # noqa: E402
    CaseAnalysis,
    _infer_department,
    build_case_analysis,
)


def _agg(
    *,
    citations: list[Citation] | None = None,
    agents: dict | None = None,
) -> AgentResult:
    return AgentResult(
        agent="AI Manager",
        payload={"agents": agents or {}},
        citations=citations or [],
        confidence=0.0,
    )


def test_infer_department_from_path_segments() -> None:
    assert _infer_department(r"KB\Raw\Credit\rules.pdf") == "Credit"
    assert _infer_department("Risk Management Policy v3") == "Risk"
    assert _infer_department(r"KB\Lotus\HR\2026\hiring.docx") == "HR"
    assert _infer_department("AML / KYC procedure") == "Compliance"
    assert _infer_department("kazna operations memo") in {"Treasury", "Operations"}


def test_infer_department_returns_none_when_no_match() -> None:
    assert _infer_department(None) is None
    assert _infer_department("Random Document") is None


def test_build_uses_metodist_text_as_summary_when_present() -> None:
    agg = _agg(
        agents={
            "AI Metodist": {
                "mode": "compare",
                "text": "Metodist xulosa: 3 ta konflikt topildi.",
            },
            "AI Searcher": {"matches": [{"snippet": "irrelevant", "score": 0.9}]},
        },
    )
    case = build_case_analysis(agg)
    assert case.summary == "Metodist xulosa: 3 ta konflikt topildi."


def test_build_falls_back_to_searcher_snippet_when_metodist_silent() -> None:
    agg = _agg(
        agents={
            "AI Searcher": {
                "matches": [{"snippet": "Top-1 retrieval hit", "score": 0.92}]
            }
        }
    )
    case = build_case_analysis(agg)
    assert case.summary == "Top-1 retrieval hit"


def test_build_collects_internal_impacts_from_citations() -> None:
    citations = [
        Citation(
            document_id="doc-1",
            title=r"KB\Raw\Credit\Credit Policy.pdf",
            snippet="Article 4.2 — loan classification.",
            score=0.91,
        ),
        Citation(
            document_id="doc-2",
            title=r"KB\Raw\Risk\Risk Framework.pdf",
            snippet="Section 7.1 — concentration limits.",
            score=0.84,
        ),
    ]
    case = build_case_analysis(_agg(citations=citations))
    assert len(case.affected_internal) == 2
    titles = [i.title for i in case.affected_internal]
    assert r"KB\Raw\Credit\Credit Policy.pdf" in titles
    depts = [i.department for i in case.affected_internal]
    assert "Credit" in depts
    assert "Risk" in depts


def test_build_aggregates_unique_departments_in_order() -> None:
    citations = [
        Citation(
            document_id="c1",
            title=r"KB\Raw\Credit\a.pdf",
            snippet="x",
            score=0.9,
        ),
        Citation(
            document_id="c2",
            title=r"KB\Raw\Risk\b.pdf",
            snippet="y",
            score=0.8,
        ),
        Citation(
            document_id="c3",
            title=r"KB\Raw\Credit\c.pdf",
            snippet="z",
            score=0.7,
        ),
    ]
    case = build_case_analysis(_agg(citations=citations))
    assert case.affected_departments == ["Credit", "Risk"]


def test_build_picks_up_external_basis_from_metodist_chunks() -> None:
    agg = _agg(
        agents={
            "AI Metodist": {
                "text": "ok",
                "external_chunks": [
                    {
                        "source_url": "https://cbu.uz/circulars/2025-14.pdf",
                        "document_number": "Циркуляр №2025/14",
                        "authority": None,
                        "text": "Об установлении норматива достаточности капитала…",
                    },
                    {
                        "source_url": "https://lex.uz/docs/55555",
                        "document_number": "ЎзР Қонуни 250-сон",
                        "text": "О банках и банковской деятельности",
                    },
                    {
                        # Not a real URL — should be ignored.
                        "source_url": "n/a",
                        "text": "garbage",
                    },
                ],
            }
        }
    )
    case = build_case_analysis(agg)
    assert len(case.external_basis) == 2
    authorities = {e.authority for e in case.external_basis}
    assert authorities == {"cbu.uz", "lex.uz"}


def test_build_returns_empty_case_for_empty_aggregate() -> None:
    case = build_case_analysis(_agg())
    assert isinstance(case, CaseAnalysis)
    assert case.summary == ""
    assert case.affected_internal == []
    assert case.external_basis == []
    assert case.conflicts == []
    assert case.recommendations == []
    assert case.affected_departments == []


def test_to_dict_is_json_serialisable() -> None:
    import json

    agg = _agg(
        citations=[
            Citation(
                document_id="d1",
                title=r"KB\Raw\Compliance\kyc.pdf",
                snippet="KYC obligation",
                score=0.81,
            )
        ],
        agents={"AI Metodist": {"text": "summary"}},
    )
    body = build_case_analysis(agg).to_dict()
    # Round-trip through JSON — guards against non-serialisable types
    # creeping into the dataclass field types.
    serialised = json.dumps(body)
    parsed = json.loads(serialised)
    assert parsed["summary"] == "summary"
    assert parsed["affected_departments"] == ["Compliance"]
    assert parsed["affected_internal"][0]["department"] == "Compliance"
