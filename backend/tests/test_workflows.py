"""Tests for per-case workflow templates."""

from __future__ import annotations

import os

os.environ.setdefault("AIM_ROOT", "/tmp/aim-root-wf-test")

from app.agents.workflows import template_for


def test_general_template_is_minimal() -> None:
    t = template_for("general")
    assert t.case_type == "general"
    assert t.extra_agents == set()
    assert t.metodist_mode is None
    assert t.directive == ""


def test_incoming_letter_forces_metodist_compare() -> None:
    t = template_for("incoming_letter")
    assert "AI Metodist" in t.extra_agents
    assert t.metodist_mode == "compare"
    assert "taqqosla" in t.directive.lower()


def test_product_check_pulls_shadow_and_metodist() -> None:
    t = template_for("product_check")
    assert {"AI Metodist", "AI Shadow"} <= t.extra_agents
    assert t.metodist_mode == "compare"
    assert "lotus" in t.directive.lower()


def test_normative_audit_forces_compare() -> None:
    t = template_for("normative_audit")
    assert "AI Metodist" in t.extra_agents
    assert t.metodist_mode == "compare"
    assert "ssilka" in t.directive.lower() or "manba" in t.directive.lower()


def test_unknown_case_type_falls_back_to_general() -> None:
    t = template_for("nonexistent")
    assert t.case_type == "general"
    assert t.extra_agents == set()
