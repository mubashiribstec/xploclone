"""API tests — routing, validation, voices, Urdu 503, auth (no GPU).

The engine is faked in conftest.py (sine tone). These tests prove the
HTTP contract, not voice quality.
"""

from tests.conftest import AUTH


def test_health(client) -> None:  # type: ignore[no-untyped-def]
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    # Liveness is "ok" even when no engine is loaded (m7); readiness is separate.
    assert body["ready"] is False
    assert body["chatterbox_revision_resolved"] is None
    assert body["engines"]["ur"] == "unavailable"


def test_voices_lists_only_three(client) -> None:  # type: ignore[no-untyped-def]
    r = client.get("/v1/voices")
    assert r.status_code == 200
    voices = r.json()["voices"]
    assert [v["voice_id"] for v in voices] == [
        "mubashir-en-us",
        "mubashir-en-gb",
        "mubashir-ur",
    ]
    urdu = voices[2]
    assert urdu["status"] == "unavailable"
    assert urdu["engine"] == "tbd-urdu-spike"


def test_metrics_endpoint(client) -> None:  # type: ignore[no-untyped-def]
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "xploclone_requests_total" in r.text


def test_tts_requires_auth(client) -> None:  # type: ignore[no-untyped-def]
    r = client.post("/v1/tts", json={"voice_id": "mubashir-en-gb", "text": "Hello."})
    assert r.status_code == 401


def test_tts_wrong_key_rejected(client) -> None:  # type: ignore[no-untyped-def]
    r = client.post(
        "/v1/tts",
        json={"voice_id": "mubashir-en-gb", "text": "Hello."},
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert r.status_code == 401


def test_tts_unknown_voice_400(client) -> None:  # type: ignore[no-untyped-def]
    r = client.post(
        "/v1/tts",
        json={"voice_id": "mubashir-en-xx", "text": "Hello."},
        headers=AUTH,
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "unknown_voice"


def test_tts_empty_text_400(client) -> None:  # type: ignore[no-untyped-def]
    r = client.post("/v1/tts", json={"voice_id": "mubashir-en-gb", "text": "   "}, headers=AUTH)
    assert r.status_code == 400


def test_tts_too_long_400(client) -> None:  # type: ignore[no-untyped-def]
    r = client.post(
        "/v1/tts",
        json={"voice_id": "mubashir-en-gb", "text": "x" * 5001},
        headers=AUTH,
    )
    # Over-long text is a 400 with code text_too_long (m1), not Pydantic 422.
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "text_too_long"


def test_tts_urdu_503_never_falls_back(client) -> None:  # type: ignore[no-untyped-def]
    r = client.post(
        "/v1/tts",
        json={"voice_id": "mubashir-ur", "text": "Assalam o alaikum."},
        headers=AUTH,
    )
    assert r.status_code == 503
    assert r.json()["detail"]["code"] == "engine_unavailable"


def test_tts_unsupported_format_400(client) -> None:  # type: ignore[no-untyped-def]
    r = client.post(
        "/v1/tts",
        json={"voice_id": "mubashir-en-gb", "text": "Hello.", "format": "mp3"},
        headers=AUTH,
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "unsupported_format"


def test_tts_success_wav(client) -> None:  # type: ignore[no-untyped-def]
    r = client.post(
        "/v1/tts",
        json={"voice_id": "mubashir-en-gb", "text": "Hello, this is a test."},
        headers=AUTH,
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/wav")
    assert r.headers["X-XploClone-Voice"] == "mubashir-en-gb"
    # Watermark is "perth-unverified" until the GPU survival test passes (m8).
    assert r.headers["X-Watermark"] == "perth-unverified"
    assert r.content[:4] == b"RIFF"  # WAV header


def test_tts_success_pcm16(client) -> None:  # type: ignore[no-untyped-def]
    r = client.post(
        "/v1/tts",
        json={"voice_id": "mubashir-en-us", "text": "Hello.", "format": "pcm16"},
        headers=AUTH,
    )
    assert r.status_code == 200
    assert "audio/L16" in r.headers["content-type"]


def test_tts_lowercase_bearer_accepted(client) -> None:  # type: ignore[no-untyped-def]
    """m5: 'bearer' (lowercase) is the same credential as 'Bearer' —
    auth and rate limiting both key on the token, not the header spelling."""
    r = client.post(
        "/v1/tts",
        json={"voice_id": "mubashir-en-us", "text": "Hello."},
        headers={"Authorization": "bearer test-key"},
    )
    assert r.status_code == 200


def test_synthesis_failure_is_503_not_500(client, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """An unexpected synthesis error (m10) is a 503 synthesis_failed, not a bare 500."""

    def boom(voice_id: str, chunks: list[str], prosody=None):  # type: ignore[no-untyped-def]
        raise RuntimeError("torch OOM (simulated)")

    from api.engine import REGISTRY

    monkeypatch.setattr(REGISTRY, "synthesize", boom)
    r = client.post(
        "/v1/tts",
        json={"voice_id": "mubashir-en-gb", "text": "Hello."},
        headers=AUTH,
    )
    assert r.status_code == 503
    assert r.json()["detail"]["code"] == "synthesis_failed"
    assert "OOM" not in r.json()["detail"]["message"]


def test_health_responsive_during_synthesis(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """M2: a blocking synthesis must not stall /health (synthesis runs via to_thread)."""
    import asyncio
    import time

    from httpx import ASGITransport, AsyncClient

    from api.audio import sine_pcm16
    from api.engine import REGISTRY, SynthesisResult
    from api.main import app

    def slow_synthesize(voice_id: str, chunks: list[str], prosody=None) -> SynthesisResult:  # type: ignore[no-untyped-def]
        time.sleep(0.8)  # blocking work, as a real GPU generate would be
        return SynthesisResult(pcm16=sine_pcm16(0.1), chunks=len(chunks))

    monkeypatch.setattr(REGISTRY, "synthesize", slow_synthesize)
    monkeypatch.setattr(REGISTRY, "has_reference", lambda voice_id: voice_id != "mubashir-ur")

    async def _run() -> tuple[float, int, int]:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            task = asyncio.create_task(
                ac.post(
                    "/v1/tts",
                    json={"voice_id": "mubashir-en-gb", "text": "Hello."},
                    headers=AUTH,
                )
            )
            await asyncio.sleep(0.2)
            t0 = time.monotonic()
            health = await ac.get("/health")
            health_elapsed = time.monotonic() - t0
            tts = await task
            return health_elapsed, health.status_code, tts.status_code

    health_elapsed, health_status, tts_status = asyncio.run(_run())
    assert health_status == 200
    assert tts_status == 200
    assert health_elapsed < 0.5, f"/health was blocked by synthesis ({health_elapsed:.2f}s)"
