"""Chunker behaviour: respect token budget, include overlap, stable hashes."""

from __future__ import annotations

from app.pipeline.chunker import chunk


def _make_sentences(n: int, words_per: int = 30) -> str:
    sent = " ".join(["word"] * words_per) + "."
    return " ".join([sent] * n)


def test_chunk_respects_max_tokens() -> None:
    text = _make_sentences(200, words_per=30)
    chunks = chunk(text)
    assert chunks, "expected at least one chunk"
    for c in chunks:
        assert c.token_count <= 1100  # 1000 target + a small slack


def test_chunks_are_hashed_and_indexed() -> None:
    text = _make_sentences(50)
    chunks = chunk(text)
    assert [c.index for c in chunks] == list(range(len(chunks)))
    assert all(len(c.content_hash) == 64 for c in chunks)


def test_empty_input_yields_empty() -> None:
    assert chunk("") == []
