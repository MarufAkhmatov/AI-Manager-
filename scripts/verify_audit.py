"""One-shot verifier for the append-only audit log.

Walks every line under Logs\\audit\\audit.jsonl and confirms each entry's
`prev` field matches the sha256 of the previous line. Exit code 0 if the
chain is intact, 1 otherwise.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "backend")

from app.security.audit import verify  # noqa: E402


def main() -> int:
    ok, n, bad = verify()
    if ok:
        print(f"audit chain OK — {n} entries")
        return 0
    print(f"audit chain BROKEN at line {n}")
    if bad:
        print(f"  offending line: {bad}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
