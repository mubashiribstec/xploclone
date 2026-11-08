"""Tag-policy + humanize tests (gap A4, prosody pipeline step 3).

No GPU: pure text functions, plus API tests proving the pipeline
runs on real requests (the fake engine captures the chunks it was
given, so the test can see exactly what the model would have heard).
"""

from api.normalize import apply_tag_policy, humanize_text, normalize_text
from tests.conftest import AUTH


def test_whitelisted_tags_kept_in_file_generation() -> None:
    out = apply_tag_policy("That was funny [laugh] and then [sigh] quiet.", allow_tags=True)
    assert "[laugh]" in out
    assert "[sigh]" in out


def test_non_whitelisted_tag_stripped() -> None:
    """Tag injection: [scream] etc. must never reach the model."""
    out = apply_tag_policy("Hello [scream] world [evil-laugh] done.", allow_tags=True)
    assert "[scream]" not in out
    assert "evil-laugh" not in out
    assert "Hello" in out and "world" in out


def test_tag_match_is_case_insensitive() -> None:
    assert "[laugh]" in apply_tag_policy("Ha [LAUGH] ha.", allow_tags=True)


def test_live_call_path_strips_all_tags() -> None:
    """Phase 3 default: a phone call never laughs/sighs on text's say-so."""
    out = apply_tag_policy("That was funny [laugh] and [sigh] quiet.", allow_tags=False)
    assert "[laugh]" not in out
    assert "[sigh]" not in out
    assert "funny" in out


def test_stray_bracket_without_close_is_left_alone() -> None:
    assert "a [ b" in apply_tag_policy("a [ b", allow_tags=True)


def test_humanize_line_break_becomes_sentence_break() -> None:
    out = humanize_text("First line here\nSecond line here")
    assert out == "First line here. Second line here."


def test_humanize_long_sentence_splits_at_comma() -> None:
    long = (
        "Our website offers more than two hundred and fifty free tools for everyday work, "
        "you can merge PDF files, convert images, compress large files, and calculate your age, "
        "your salary, and your loan payments, all without creating an account."
    )
    out = humanize_text(long)
    assert out.count(".") >= 2
    # Words are unchanged — only punctuation breaks were inserted
    # (the split capitalises the second sentence's first word).
    assert (
        out.replace(".", "").replace(",", "").lower().split()
        == long.replace(",", "").replace(".", "").lower().split()
    )
    for sentence in out.split(". "):
        assert len(sentence) <= 180 or "," not in sentence


def test_humanize_short_text_unchanged() -> None:
    assert humanize_text("Hello, thank you for calling.") == "Hello, thank you for calling."


def test_humanize_never_adds_breath_or_noise() -> None:
    out = humanize_text("Hello there. How are you?")
    assert "breath" not in out.lower()
    assert "[sigh]" not in out
    assert out == "Hello there. How are you?"


def test_normalize_keeps_pause_distinction() -> None:
    """Em-dash and ellipsis are different pauses from a comma —
    they must not all collapse to ', ' (the old behaviour)."""
    assert normalize_text("Hello — she said.") == "Hello - she said."
    assert normalize_text("Wait… what?") == "Wait. what?"


def test_api_tag_injection_stripped_before_synthesis(client, monkeypatch) -> None:
    """End-to-end: [scream] is stripped, [laugh] survives, before the
    engine ever sees the text."""
    from api.audio import sine_pcm16
    from api.engine import REGISTRY, SynthesisResult

    seen: list[list[str]] = []

    def capturing(voice_id: str, chunks: list[str], prosody=None) -> SynthesisResult:
        seen.append(list(chunks))
        return SynthesisResult(pcm16=sine_pcm16(0.1), chunks=len(chunks))

    monkeypatch.setattr(REGISTRY, "synthesize", capturing)
    r = client.post(
        "/v1/tts",
        json={
            "voice_id": "mubashir-en-gb",
            "text": "That was funny [laugh] but not [scream] scary.",
        },
        headers=AUTH,
    )
    assert r.status_code == 200
    joined = " ".join(seen[0])
    assert "[laugh]" in joined
    assert "[scream]" not in joined


def test_api_preset_headers_and_defaults(client) -> None:
    """Default request: preset header says 'default', and the honest
    effective flags say exaggeration/CFG did NOT act on Turbo."""
    r = client.post(
        "/v1/tts",
        json={"voice_id": "mubashir-en-gb", "text": "Hello, preset header test."},
        headers=AUTH,
    )
    assert r.status_code == 200
    assert r.headers["X-XploClone-Preset"] == "default"
    assert r.headers["X-Prosody-Exaggeration-Effective"] == "false"
    assert r.headers["X-Prosody-CFG-Effective"] == "false"


def test_api_natural_preset_accepted(client) -> None:
    r = client.post(
        "/v1/tts",
        json={
            "voice_id": "mubashir-en-gb",
            "text": "Hello, natural preset test.",
            "preset": "natural",
        },
        headers=AUTH,
    )
    assert r.status_code == 200
    assert r.headers["X-XploClone-Preset"] == "natural"


def test_api_unknown_preset_400(client) -> None:
    r = client.post(
        "/v1/tts",
        json={"voice_id": "mubashir-en-gb", "text": "Hello.", "preset": "dramatic"},
        headers=AUTH,
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "invalid_preset"


def test_api_out_of_range_exaggeration_422(client) -> None:
    r = client.post(
        "/v1/tts",
        json={"voice_id": "mubashir-en-gb", "text": "Hello.", "exaggeration": 1.5},
        headers=AUTH,
    )
    assert r.status_code == 422


def test_api_cache_key_includes_prosody(client) -> None:
    """Same text, different preset: the second preset must be a cache
    MISS (different audio), not a hit returning the first preset's take."""
    text = "Cache must respect the preset, uniquely worded request."
    r1 = client.post(
        "/v1/tts",
        json={"voice_id": "mubashir-en-gb", "text": text, "preset": "natural"},
        headers=AUTH,
    )
    assert r1.headers["X-Cache"] == "miss"
    r2 = client.post(
        "/v1/tts",
        json={"voice_id": "mubashir-en-gb", "text": text, "preset": "natural"},
        headers=AUTH,
    )
    assert r2.headers["X-Cache"] == "hit"
    r3 = client.post(
        "/v1/tts",
        json={"voice_id": "mubashir-en-gb", "text": text, "preset": "firm"},
        headers=AUTH,
    )
    assert r3.headers["X-Cache"] == "miss"
