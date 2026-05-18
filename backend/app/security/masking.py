"""PII masking rules.

Applied by AI Secure on every outbound payload. Patterns target
Uzbek-context identifiers (phone, bank card / account, INN/PINFL)
plus a conservative name heuristic. NER is intentionally left out
of this phase to keep latency in the perf budget; the regexes cover
the high-impact cases without dragging in a model.
"""

from __future__ import annotations

import re

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Uzbek mobile: +998 XX XXX XX XX (with or without spaces / dashes)
    (re.compile(r"\+?998[\s\-]?\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"), "[PHONE]"),
    # Generic 10–15 digit phone fallback
    (re.compile(r"(?<!\d)\+?\d{10,15}(?!\d)"), "[PHONE]"),
    # Bank card (13–19 digits, optional 4-grouped)
    (re.compile(r"(?<!\d)(?:\d{4}[\s\-]?){3,4}\d{1,4}(?!\d)"), "[CARD]"),
    # Bank account (20+ digit IBAN-ish)
    (re.compile(r"(?<!\d)\d{20,28}(?!\d)"), "[ACCOUNT]"),
    # Uzbek INN/PINFL (14 digits)
    (re.compile(r"(?<!\d)\d{14}(?!\d)"), "[ID]"),
    # Email
    (re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), "[EMAIL]"),
    # Conservative person-name heuristic: two consecutive Capitalized words
    # (Cyrillic or Latin) of length >= 2. Avoids common headings like
    # "Glava 1" by requiring both tokens be alpha.
    (
        re.compile(
            r"\b([A-ZА-ЯЎҚҒҲ][a-zа-яўқғҳ]{2,})\s+([A-ZА-ЯЎҚҒҲ][a-zа-яўқғҳ]{2,})\b"
        ),
        "[NAME]",
    ),
]


def mask_text(text: str) -> str:
    out = text
    for pat, repl in _PATTERNS:
        out = pat.sub(repl, out)
    return out
