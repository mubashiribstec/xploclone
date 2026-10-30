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
    assert r.status_code == 422  # pydantic max_length on the request model


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
    assert r.headers["X-Watermark"] == "perth-preserved"
    assert r.content[:4] == b"RIFF"  # WAV header


def test_tts_success_pcm16(client) -> None:  # type: ignore[no-untyped-def]
    r = client.post(
        "/v1/tts",
        json={"voice_id": "mubashir-en-us", "text": "Hello.", "format": "pcm16"},
        headers=AUTH,
    )
    assert r.status_code == 200
    assert "audio/L16" in r.headers["content-type"]
