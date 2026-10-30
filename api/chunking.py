"""Sentence chunking for streaming TTS (PLAN-v2 §6.2/§6.4).

Long text is split at sentence boundaries so the engine can start speaking
before the whole request is synthesised, and so a single failure does not
lose the whole utterance. Chunks are never silently truncated: if a single
sentence exceeds ``max_chunk_chars`` it is split at clause boundaries
(commas / semicolons), and only as a last resort at a word boundary.
"""

from __future__ import annotations

import re

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'“\(])")
_CLAUSE_RE = re.compile(r"(?<=[,;:])\s+")

DEFAULT_MAX_CHUNK_CHARS = 400


def split_sentences(text: str) -> list[str]:
    """Split text into sentences. Returns [] for blank input."""
    text = re.sub(r"\s+", " ", text.strip())
    if not text:
        return []
    parts = _SENTENCE_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def chunk_text(text: str, max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS) -> list[str]:
    """Split text into synthesis chunks of at most ``max_chunk_chars``.

    Short sentences are joined with a space until the limit is reached, so
    the engine keeps natural prosody across short clauses.
    """
    sentences = split_sentences(text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        pieces = [sentence]
        if len(sentence) > max_chunk_chars:
            pieces = _split_long_sentence(sentence, max_chunk_chars)
        for piece in pieces:
            if not current:
                current = piece
            elif len(current) + 1 + len(piece) <= max_chunk_chars:
                current = current + " " + piece
            else:
                chunks.append(current)
                current = piece
    if current:
        chunks.append(current)
    return chunks


def _split_long_sentence(sentence: str, max_chunk_chars: int) -> list[str]:
    clauses = _CLAUSE_RE.split(sentence)
    out: list[str] = []
    current = ""
    for clause in clauses:
        if len(clause) > max_chunk_chars:
            # Last resort: hard split on word boundaries.
            words = clause.split(" ")
            for word in words:
                if not current:
                    current = word
                elif len(current) + 1 + len(word) <= max_chunk_chars:
                    current = current + " " + word
                else:
                    out.append(current)
                    current = word
        elif not current:
            current = clause
        elif len(current) + 1 + len(clause) <= max_chunk_chars:
            current = current + " " + clause
        else:
            out.append(current)
            current = clause
    if current:
        out.append(current)
    return out
