"""Unit tests for sentence chunking (api/chunking.py)."""

from api.chunking import chunk_text, split_sentences


def test_split_sentences() -> None:
    assert split_sentences("Hello world. How are you? Fine!") == [
        "Hello world.",
        "How are you?",
        "Fine!",
    ]


def test_split_blank() -> None:
    assert split_sentences("   ") == []


def test_short_text_is_one_chunk() -> None:
    assert chunk_text("Hello world. Short text.") == ["Hello world. Short text."]


def test_long_text_splits_at_sentences() -> None:
    text = " ".join(f"Sentence number {i} is here." for i in range(30))
    chunks = chunk_text(text, max_chunk_chars=100)
    assert len(chunks) > 1
    assert all(len(c) <= 100 for c in chunks)
    assert " ".join(chunks).replace("  ", " ") == text


def test_no_chunk_is_silently_truncated() -> None:
    text = "First sentence here. Second sentence here. Third sentence here."
    chunks = chunk_text(text, max_chunk_chars=1000)
    assert "".join(chunks) == text


def test_very_long_sentence_splits() -> None:
    text = "word " * 200
    chunks = chunk_text(text.strip() + ".", max_chunk_chars=100)
    assert all(len(c) <= 100 for c in chunks)
    assert len(chunks) > 1
