"""Filesystem confinement.

Every read/write that touches user-controlled or KB-derived paths must
go through `safe_join`. It rejects:

- absolute paths that escape the root,
- relative paths containing `..` traversal,
- symlinks anywhere in the resolved chain (the linked target may be
  outside the root, defeating confinement),
- non-existent intermediate symlinks (defensive — Windows behaves
  differently from POSIX here).
"""

from __future__ import annotations

import os
from pathlib import Path


class PathConfinementError(ValueError):
    """Raised when a requested path would escape the configured root."""


def _resolve_no_symlinks(p: Path) -> Path:
    """Resolve `p` to an absolute path without crossing any symlink.

    `Path.resolve()` follows symlinks; we walk the chain ourselves and
    raise if any segment that *exists* is a link. We use `os.path.lexists`
    + `Path.is_symlink()` so this works on Python 3.11 (where
    `Path.exists(follow_symlinks=False)` doesn't exist yet).
    """
    p = Path(os.path.normpath(str(p)))
    if not p.is_absolute():
        p = Path.cwd() / p

    accumulated = Path(p.anchor)
    for part in p.parts[1:]:
        accumulated = accumulated / part
        if os.path.lexists(accumulated) and accumulated.is_symlink():
            raise PathConfinementError(f"symlink not allowed in path: {accumulated}")
    return accumulated


def safe_join(root: Path, *parts: str | os.PathLike[str]) -> Path:
    """Return `root / parts...` after confirming the result stays under `root`.

    The result is an absolute, normalized path; intermediate directories
    are not created. Callers requesting creation should subsequently
    `mkdir(parents=True, exist_ok=True)` on the returned path.
    """
    if not parts:
        candidate = root
    else:
        # Reject absolute components outright: they'd silently replace the root.
        for part in parts:
            sp = os.fspath(part)
            if sp.startswith(("/", "\\")) or (len(sp) > 1 and sp[1] == ":"):
                raise PathConfinementError(f"absolute component not allowed: {sp!r}")
        candidate = Path(root).joinpath(*[os.fspath(p) for p in parts])

    resolved_root = _resolve_no_symlinks(Path(root))
    resolved = _resolve_no_symlinks(candidate)

    try:
        resolved.relative_to(resolved_root)
    except ValueError as e:
        raise PathConfinementError(
            f"path {resolved} is outside root {resolved_root}"
        ) from e

    return resolved
