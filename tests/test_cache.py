"""Audio-cache tests — identical requests must hit the cache (no model).

The cache stores PCM16 keyed by (voice_id, normalised text, format).
A second identical request must not call synthesize again.
"""

from tests.conftest import AUTH


def test_cache_second_identical_request_is_a_hit(client, monkeypatch) -> None:
    """First request misses, second identical request hits the cache."""
    from api.main import AUDIO_CACHE

    AUDIO_CACHE.clear()
    calls = {"n": 0}
    from api.engine import REGISTRY

    orig = REGISTRY.synthesize

    def counting(voice_id: str, chunks: list[str]):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        return orig(voice_id, chunks)

    monkeypatch.setattr(REGISTRY, "synthesize", counting)
    body = {"voice_id": "mubashir-en-gb", "text": "Hello, cache test."}
    r1 = client.post("/v1/tts", json=body, headers=AUTH)
    assert r1.status_code == 200
    assert r1.headers["X-Cache"] == "miss"
    assert calls["n"] == 1
    r2 = client.post("/v1/tts", json=body, headers=AUTH)
    assert r2.status_code == 200
    assert r2.headers["X-Cache"] == "hit"
    assert calls["n"] == 1, "second identical request must not re-synthesise"
    assert r2.content == r1.content


def test_cache_miss_on_different_text(client) -> None:
    """A different text is a different cache key."""
    from api.main import AUDIO_CACHE

    AUDIO_CACHE.clear()
    r1 = client.post(
        "/v1/tts", json={"voice_id": "mubashir-en-gb", "text": "First sentence."}, headers=AUTH
    )
    r2 = client.post(
        "/v1/tts", json={"voice_id": "mubashir-en-gb", "text": "Second sentence."}, headers=AUTH
    )
    assert r1.headers["X-Cache"] == "miss"
    assert r2.headers["X-Cache"] == "miss"
    # Both responses are the same fake sine tone in tests; the point
    # asserted here is only that different text does not hit the cache.


def test_cache_metrics_exposed(client) -> None:
    """GET /metrics reports cache hits/misses."""
    from api.main import AUDIO_CACHE

    AUDIO_CACHE.clear()
    body = {"voice_id": "mubashir-en-gb", "text": "Metrics cache test."}
    client.post("/v1/tts", json=body, headers=AUTH)
    client.post("/v1/tts", json=body, headers=AUTH)
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "xploclone_audio_cache_hits" in r.text
    assert "xploclone_audio_cache_misses" in r.text
