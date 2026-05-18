"""Audit chain integrity."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.config import get_settings
from app.security import audit


@pytest.fixture
def fresh_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AIM_ROOT", str(tmp_path))
    get_settings.cache_clear()
    (tmp_path / "Logs" / "audit").mkdir(parents=True)
    return tmp_path


def test_chain_is_walkable(fresh_root: Path) -> None:
    asyncio.run(audit.record("test.one", a=1))
    asyncio.run(audit.record("test.two", a=2))
    asyncio.run(audit.record("test.three", a=3))
    ok, n, bad = audit.verify()
    assert ok is True
    assert n == 3
    assert bad is None


def test_tampering_is_detected(fresh_root: Path) -> None:
    asyncio.run(audit.record("test.one", a=1))
    asyncio.run(audit.record("test.two", a=2))
    p = fresh_root / "Logs" / "audit" / "audit.jsonl"
    contents = p.read_text().splitlines()
    contents[0] = contents[0].replace("test.one", "test.tampered")
    p.write_text("\n".join(contents) + "\n")
    ok, n, _ = audit.verify()
    assert ok is False
    assert n == 2
