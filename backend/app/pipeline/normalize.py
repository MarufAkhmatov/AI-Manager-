"""Stage 4: text normalization.

Unicode NFC, soft-hyphen + dehyphenation across line breaks, whitespace
collapse, and detection of obvious section headings.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_HYPHEN_LINE = re.compile(r"(\w)-\n(\w)")
_MULTISPACE = re.compile(r"[ \t]+")
_MULTINEWLINE = re.compile(r"\n{3,}")
_SOFT_HYPHEN = "­"
_HEADING_RE = re.compile(
    r"^(?:(?:[IVXLCM]+\.)|(?:\d+(?:\.\d+){0,3}\.?))\s+\S",
    re.MULTILINE,
)


@dataclass(slots=True)
class Normalized:
    text: str
    headings: list[str]


def normalize(text: str) -> Normalized:
    t = unicodedata.normalize("NFC", text).replace(_SOFT_HYPHEN, "")
    t = _HYPHEN_LINE.sub(r"\1\2", t)
    t = _MULTISPACE.sub(" ", t)
    t = _MULTINEWLINE.sub("\n\n", t).strip()
    headings = [m.group(0).strip() for m in _HEADING_RE.finditer(t)]
    return Normalized(text=t, headings=headings)
