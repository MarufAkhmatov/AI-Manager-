"""Path-confinement contract tests for the safe_join helper."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from app.security.paths import PathConfinementError, safe_join


def test_safe_join_simple(tmp_path: Path) -> None:
    out = safe_join(tmp_path, "KB", "Raw", "file.pdf")
    assert out == tmp_path / "KB" / "Raw" / "file.pdf"


def test_safe_join_rejects_dotdot(tmp_path: Path) -> None:
    with pytest.raises(PathConfinementError):
        safe_join(tmp_path, "..", "outside.txt")


def test_safe_join_rejects_absolute_component(tmp_path: Path) -> None:
    abs_attempt = "/etc/passwd" if sys.platform != "win32" else r"C:\Windows\System32\evil.txt"
    with pytest.raises(PathConfinementError):
        safe_join(tmp_path, abs_attempt)


@pytest.mark.skipif(sys.platform == "win32", reason="symlink permissions differ on Windows")
def test_safe_join_rejects_symlink(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside_target"
    outside.mkdir(exist_ok=True)
    link = tmp_path / "KB"
    os.symlink(outside, link, target_is_directory=True)
    with pytest.raises(PathConfinementError):
        safe_join(tmp_path, "KB", "anything")


def test_safe_join_root_only(tmp_path: Path) -> None:
    assert safe_join(tmp_path) == tmp_path
