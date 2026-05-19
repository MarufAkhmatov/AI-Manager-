"""Unit tests for the Markdown sidecar that ``persist_chunks`` writes
alongside ``chunks.jsonl``. The DB write half of ``persist_chunks`` needs
Postgres + pgvector; here we exercise only the frontmatter generation +
file-layout contract directly.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

# Keep the platform settings happy before importing the module.
os.environ.setdefault("AIM_ROOT", "/tmp/aim-root-sidecar-test")
os.makedirs(os.environ["AIM_ROOT"], exist_ok=True)

from app.pipeline import storage  # noqa: E402


class _StubDoc:
    """Stand-in for the SQLAlchemy Document row. Mirrors the attributes
    the frontmatter helper reads."""

    def __init__(
        self,
        *,
        title: str | None,
        category: str,
        authority: str | None = None,
        source_url: str | None = None,
        is_confidential: bool = False,
    ) -> None:
        self.id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        self.sha256 = "a" * 64
        self.title = title
        self.category = category
        self.authority = authority
        self.source_url = source_url
        self.raw_path = r"C:\Users\ASUS\Desktop\AI Manager\KB\Regulator\cbu.uz\circular.pdf"
        self.status = "active"
        self.is_confidential = is_confidential
        self.ingested_at = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)


def test_frontmatter_contains_core_metadata() -> None:
    doc = _StubDoc(
        title="CBU Circular 2025/14",
        category="regulator",
        authority="cbu.uz",
        source_url="https://cbu.uz/circulars/2025-14.pdf",
    )
    fm = storage._frontmatter(doc, headings=["1. General", "2. Scope"])
    assert fm.startswith("---")
    assert fm.endswith("---")
    assert 'title: "CBU Circular 2025/14"' in fm
    assert "document_id: 11111111-1111-1111-1111-111111111111" in fm
    assert "sha256: " + "a" * 64 in fm
    assert 'category: "regulator"' in fm
    assert 'authority: "cbu.uz"' in fm
    assert 'source_url: "https://cbu.uz/circulars/2025-14.pdf"' in fm
    assert "is_confidential: false" in fm
    assert "ingested_at: 2026-05-18T12:00:00+00:00" in fm
    assert "headings:" in fm
    assert '  - "1. General"' in fm
    assert '  - "2. Scope"' in fm


def test_frontmatter_handles_none_fields() -> None:
    doc = _StubDoc(
        title=None, category="raw", authority=None, source_url=None
    )
    fm = storage._frontmatter(doc, headings=[])
    assert 'title: ""' in fm
    assert 'authority: ""' in fm
    assert 'source_url: ""' in fm
    # No headings block when there's nothing to list.
    assert "headings:" not in fm


def test_frontmatter_escapes_embedded_quotes_and_newlines() -> None:
    doc = _StubDoc(
        title='He said "hello"\nand left', category="raw"
    )
    fm = storage._frontmatter(doc, headings=[])
    assert 'title: "He said \\"hello\\" and left"' in fm
    # No raw newline mid-value — the frontmatter must stay parseable.
    title_line = next(line for line in fm.splitlines() if line.startswith("title:"))
    assert "\n" not in title_line


def test_frontmatter_marks_confidential_lotus() -> None:
    doc = _StubDoc(
        title="Internal HR Policy",
        category="lotus",
        authority="HR",
        is_confidential=True,
    )
    fm = storage._frontmatter(doc, headings=[])
    assert "is_confidential: true" in fm
    assert 'category: "lotus"' in fm


def test_frontmatter_caps_long_headings_list() -> None:
    doc = _StubDoc(title="Big doc", category="regulator")
    headings = [f"Section {i}" for i in range(200)]
    fm = storage._frontmatter(doc, headings=headings)
    # We cap at 50 entries so an outlier doc doesn't blow up the file.
    assert sum(1 for ln in fm.splitlines() if ln.startswith("  - ")) == 50
