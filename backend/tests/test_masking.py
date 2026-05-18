"""Smoke tests for PII masking + Shadow-guard contracts."""

from __future__ import annotations

from app.agents.base import AgentResult, Citation
from app.security.masking import mask_text
from app.security.shadow_guard import scrub


def test_mask_phone_uz() -> None:
    out = mask_text("Call +998 90 123 45 67 today")
    assert "[PHONE]" in out
    assert "+998" not in out


def test_mask_card_and_email() -> None:
    out = mask_text("card 4111 1111 1111 1111, email me at user@example.com")
    assert "[CARD]" in out
    assert "[EMAIL]" in out


def test_mask_inn_14_digits() -> None:
    assert "[ID]" in mask_text("INN: 12345678901234")


def test_mask_name_heuristic() -> None:
    assert "[NAME]" in mask_text("Signed by Aziz Karimov on Monday")


def test_shadow_guard_strips_metadata_for_confidential() -> None:
    res = AgentResult(
        agent="AI Shadow",
        payload={"document_id": "abc", "title": "Lotus Policy", "summary": "ok"},
        citations=[Citation(document_id="x", title="Lotus", snippet="...", score=0.9)],
        confidential_origin=True,
    )
    scrubbed = scrub(res)
    assert "document_id" not in scrubbed.payload
    assert "title" not in scrubbed.payload
    assert scrubbed.citations[0].document_id is None
    assert scrubbed.citations[0].title is None


def test_shadow_guard_noop_for_public() -> None:
    res = AgentResult(
        agent="AI Searcher",
        payload={"title": "Public", "summary": "ok"},
        citations=[Citation(document_id="x", title="Public", snippet="...", score=0.9)],
        confidential_origin=False,
    )
    scrubbed = scrub(res)
    assert scrubbed.payload["title"] == "Public"
    assert scrubbed.citations[0].title == "Public"
