"""Classification routing of files under AIM_ROOT."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import get_settings
from app.pipeline.classify import classify


@pytest.fixture
def aim_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AIM_ROOT", str(tmp_path))
    get_settings.cache_clear()
    for sub in (
        "KB/Regulator/lex_uz",
        "KB/Regulator/cbu_uz",
        "KB/Lotus",
        "KB/Raw",
    ):
        (tmp_path / sub).mkdir(parents=True)
    return tmp_path


def test_classify_lotus_is_confidential(aim_root: Path) -> None:
    f = aim_root / "KB/Lotus/policy.pdf"
    f.touch()
    out = classify(f)
    assert out.category == "lotus"
    assert out.is_confidential is True


def test_classify_regulator_maps_authority(aim_root: Path) -> None:
    f = aim_root / "KB/Regulator/lex_uz/act.pdf"
    f.touch()
    out = classify(f)
    assert out.category == "regulator"
    assert out.authority == "lex.uz"
    assert out.is_confidential is False


def test_classify_raw_is_internal(aim_root: Path) -> None:
    f = aim_root / "KB/Raw/whatever.pdf"
    f.touch()
    out = classify(f)
    assert out.category == "internal"
    assert out.is_confidential is False
