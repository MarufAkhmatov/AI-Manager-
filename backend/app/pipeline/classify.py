"""File classification.

Rule-based first; the LLM is the fallback (Phase 3+). Today the rules
cover the four categories we ship with and the confidentiality flag.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings

REGULATOR_AUTHORITY = {
    "lex_uz": "lex.uz",
    "cbu_uz": "cbu.uz",
    "ipakyulibank": "ipakyulibank.uz",
}


@dataclass(slots=True)
class Classification:
    category: str        # 'regulator' | 'lotus' | 'internal' | 'other'
    authority: str | None
    is_confidential: bool


def classify(path: Path) -> Classification:
    """Decide category for a file based on its location under AIM_ROOT."""
    s = get_settings()
    try:
        rel = path.resolve().relative_to(s.aim_root.resolve())
    except ValueError:
        return Classification(category="other", authority=None, is_confidential=False)

    parts = rel.parts

    # KB\Lotus\... is always confidential.
    if len(parts) >= 2 and parts[0] == "KB" and parts[1] == "Lotus":
        return Classification(category="lotus", authority=None, is_confidential=True)

    # KB\Regulator\<bucket>\...
    if len(parts) >= 3 and parts[0] == "KB" and parts[1] == "Regulator":
        bucket = parts[2]
        return Classification(
            category="regulator",
            authority=REGULATOR_AUTHORITY.get(bucket),
            is_confidential=False,
        )

    # Anything else dropped in Raw\ is internal until proven otherwise.
    if len(parts) >= 2 and parts[0] == "KB" and parts[1] == "Raw":
        return Classification(category="internal", authority=None, is_confidential=False)

    return Classification(category="other", authority=None, is_confidential=False)
