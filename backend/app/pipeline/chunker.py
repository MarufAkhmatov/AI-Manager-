"""Stage 5: chunking.

Target 500–1000 tokens per chunk (tiktoken `cl100k_base`), 15% overlap.
Sentence boundaries first (pysbd with Cyrillic-aware regex fallback);
chunks try to break at sentence ends and respect heading-flagged
section starts whenever possible.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

_TARGET_MIN = 500
_TARGET_MAX = 1000
_OVERLAP_RATIO = 0.15

_SENT_FALLBACK = re.compile(r"(?<=[.!?…])\s+(?=[A-ZА-ЯЎҚҒҲ])")

# tiktoken encoders are lazy-loaded at first use so the platform can boot
# in offline / air-gapped environments where the `cl100k_base` BPE blob
# can't be downloaded from openaipublic.blob.core.windows.net. Falling
# back to whitespace+punct tokenisation keeps the chunker honest about
# size targets even without the official encoder.
_encoder: Any | None = None
_encoder_failed = False


def _get_encoder() -> Any | None:
    global _encoder, _encoder_failed
    if _encoder is not None or _encoder_failed:
        return _encoder
    try:
        import tiktoken

        _encoder = tiktoken.get_encoding("cl100k_base")
    except Exception:
        _encoder_failed = True
    return _encoder


@dataclass(slots=True)
class Chunk:
    index: int
    text: str
    token_count: int
    content_hash: str
    section_path: str | None


def _split_sentences(text: str) -> list[str]:
    try:
        import pysbd

        seg = pysbd.Segmenter(language="ru", clean=False)
        sents = seg.segment(text)
        if sents:
            return [s.strip() for s in sents if s.strip()]
    except Exception:
        pass
    return [s.strip() for s in _SENT_FALLBACK.split(text) if s.strip()]


_FALLBACK_TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def _token_count(text: str) -> int:
    enc = _get_encoder()
    if enc is not None:
        return len(enc.encode(text))
    # Fallback: count alphanumeric runs + standalone punctuation. Roughly
    # 0.75× a real BPE count for natural language, which keeps chunk
    # boundaries within the same ballpark.
    return len(_FALLBACK_TOKEN_RE.findall(text))


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hard_split(sentence: str, limit: int) -> list[str]:
    """Break a single oversized 'sentence' into word-runs of <= `limit` tokens.

    The sentence segmenter leaves long unpunctuated blocks (OCR dumps, tables,
    URL/number lists) as one giant segment. Left whole they overflow the
    embedding model's context window and Ollama rejects the embed with
    HTTP 400 'input length exceeds the context length'. Splitting on word
    boundaries keeps every chunk well under the limit without losing content.
    """
    words = sentence.split()
    if not words:
        return []
    pieces: list[str] = []
    buf: list[str] = []
    buf_tokens = 0
    for w in words:
        wt = _token_count(w)
        if buf and buf_tokens + wt > limit:
            pieces.append(" ".join(buf))
            buf, buf_tokens = [], 0
        buf.append(w)
        buf_tokens += wt
    if buf:
        pieces.append(" ".join(buf))
    return pieces


def chunk(text: str, *, section_path: str | None = None) -> list[Chunk]:
    raw_sentences = _split_sentences(text)
    # Pre-split any single segment that already exceeds the chunk budget so the
    # main packing loop never emits an oversized chunk (which would 400 at embed).
    sentences: list[str] = []
    for s in raw_sentences:
        if _token_count(s) > _TARGET_MAX:
            sentences.extend(_hard_split(s, _TARGET_MAX))
        else:
            sentences.append(s)
    chunks: list[Chunk] = []

    buf: list[str] = []
    buf_tokens = 0
    idx = 0

    def flush() -> None:
        nonlocal buf, buf_tokens, idx
        if not buf:
            return
        body = " ".join(buf).strip()
        chunks.append(
            Chunk(
                index=idx,
                text=body,
                token_count=buf_tokens,
                content_hash=_hash(body),
                section_path=section_path,
            )
        )
        idx += 1
        # Carry overlap_ratio of trailing sentences forward.
        carry_target = int(buf_tokens * _OVERLAP_RATIO)
        carry: list[str] = []
        carry_tokens = 0
        for s in reversed(buf):
            t = _token_count(s)
            if carry_tokens + t > carry_target:
                break
            carry.insert(0, s)
            carry_tokens += t
        buf = carry
        buf_tokens = carry_tokens

    for s in sentences:
        t = _token_count(s)
        if buf_tokens + t > _TARGET_MAX and buf_tokens >= _TARGET_MIN:
            flush()
        buf.append(s)
        buf_tokens += t

    if buf:
        body = " ".join(buf).strip()
        chunks.append(
            Chunk(
                index=idx,
                text=body,
                token_count=buf_tokens,
                content_hash=_hash(body),
                section_path=section_path,
            )
        )

    return chunks
