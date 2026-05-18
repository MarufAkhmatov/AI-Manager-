"""Embedding helper with on-disk content-hash cache under Cache\embeddings."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.config import get_settings
from app.llm.ollama_client import get_ollama
from app.security.paths import safe_join


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _cache_path(h: str) -> Path:
    s = get_settings()
    cache_root = s.cache / "embeddings"
    cache_root.mkdir(parents=True, exist_ok=True)
    return safe_join(cache_root, h[:2], f"{h}.json")


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Return embeddings for `texts`, hitting the cache per-text."""
    if not texts:
        return []

    s = get_settings()
    out: list[list[float] | None] = [None] * len(texts)
    miss_idx: list[int] = []
    miss_texts: list[str] = []

    for i, t in enumerate(texts):
        h = _hash(t)
        p = _cache_path(h)
        if p.exists():
            out[i] = json.loads(p.read_text())
        else:
            miss_idx.append(i)
            miss_texts.append(t)

    if miss_texts:
        vecs = await get_ollama().embed(s.ollama_model_embed, miss_texts)
        for j, vec in zip(miss_idx, vecs, strict=True):
            out[j] = vec
            p = _cache_path(_hash(texts[j]))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(vec))

    return [v for v in out if v is not None]
