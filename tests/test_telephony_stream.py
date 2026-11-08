"""Tests for the streaming TTS WebSocket (api/telephony_stream.py).

Runs through the real FastAPI app via the shared ``client`` fixture
(fake Chatterbox engine, sine-tone PCM16). The torchaudio resample
step is stubbed at ``api.telephony_session.pcm16_to_ulaw`` (torch is
not installed in the test venv). One sentence of fake audio is 0.1 s
of sine tone = 800 μ-law bytes = exactly five 160-byte frames.
"""

from __future__ import annotations

import numpy as np
import pytest
from starlette.websockets import WebSocketDisconnect

from api.telephony_audio import lin2ulaw
from api.telephony_session import reset_state


def fake_pcm16_to_ulaw(pcm16: bytes, sample_rate: int) -> bytes:
    """Decimate PCM16 to 8 kHz, then the real lin2ulaw — stands in for
    the torchaudio resample (torch is not installed in the test venv)."""
    pcm = np.frombuffer(pcm16, dtype=np.int16)
    step = max(1, sample_rate // 8000)
    return lin2ulaw(pcm[::step])


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    reset_state()
    monkeypatch.setattr("api.telephony_session.pcm16_to_ulaw", fake_pcm16_to_ulaw)
    yield
    reset_state()


def _drain(ws, text, voice_id="mubashir-en-gb"):
    """Send one request; return (start, frames, done)."""
    ws.send_json({"voice_id": voice_id, "text": text})
    start = ws.receive_json()
    frames = [ws.receive_bytes() for _ in range(5)]  # 800 bytes / 160
    done = ws.receive_json()
    return start, frames, done


def test_stream_happy_path(client):
    with client.websocket_connect("/v1/tts/stream?key=test-key") as ws:
        start, frames, done = _drain(ws, "Hello world.")
    assert start["type"] == "start"
    assert start["sample_rate"] == 8000
    assert start["channels"] == 1
    assert start["format"] == "ulaw"
    assert start["voice"] == "mubashir-en-gb"
    assert start["engine"]
    assert len(frames) == 5
    assert all(len(frame) == 160 for frame in frames)
    assert done["type"] == "done"
    assert done["duration_s"] == pytest.approx(0.1)
    assert done["samples"] == 800
    assert done["sample_rate"] == 8000
    assert done["format"] == "ulaw"
    assert done["voice"] == "mubashir-en-gb"
    assert done["watermark"] == "perth-unverified"
    assert isinstance(done["ttfa_ms"], float) and done["ttfa_ms"] >= 0
    assert done["ttfa_ms"] <= done["gen_time_s"] * 1000
    assert isinstance(done["rtf"], float) and done["rtf"] >= 0


def test_stream_requires_auth(client):
    with client.websocket_connect("/v1/tts/stream") as ws:
        error = ws.receive_json()
        assert error == {
            "type": "error",
            "code": "unauthorized",
            "detail": "Invalid or missing API key.",
        }
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_json()
        assert exc_info.value.code == 1008


def test_stream_wrong_key(client):
    with client.websocket_connect("/v1/tts/stream?key=nope") as ws:
        error = ws.receive_json()
        assert error["type"] == "error"
        assert error["code"] == "unauthorized"


def test_stream_empty_text_then_valid_request(client):
    with client.websocket_connect("/v1/tts/stream?key=test-key") as ws:
        ws.send_json({"voice_id": "mubashir-en-gb", "text": "   "})
        error = ws.receive_json()
        assert error == {
            "type": "error",
            "code": "empty_text",
            "detail": "Text must be a non-empty string.",
        }
        # The socket stays open after a validation error.
        _, frames, done = _drain(ws, "Hello world.")
        assert len(frames) == 5
        assert done["type"] == "done"


def test_stream_text_too_long(client):
    with client.websocket_connect("/v1/tts/stream?key=test-key") as ws:
        ws.send_json({"voice_id": "mubashir-en-gb", "text": "x" * 5001})
        error = ws.receive_json()
        assert error["code"] == "text_too_long"


def test_stream_unknown_voice(client):
    with client.websocket_connect("/v1/tts/stream?key=test-key") as ws:
        ws.send_json({"voice_id": "not-a-voice", "text": "Hello world."})
        error = ws.receive_json()
        assert error["code"] == "unknown_voice"


def test_stream_urdu_unavailable_not_silent_fallback(client):
    """Urdu is gated: the socket must error, never serve another voice."""
    with client.websocket_connect("/v1/tts/stream?key=test-key") as ws:
        ws.send_json({"voice_id": "mubashir-ur", "text": "Hello world."})
        error = ws.receive_json()
        assert error["code"] == "engine_unavailable"


def test_stream_bad_json_keeps_socket_open(client):
    with client.websocket_connect("/v1/tts/stream?key=test-key") as ws:
        ws.send_text("this is not json")
        error = ws.receive_json()
        assert error["code"] == "bad_request"
        # The VoiceStudio original dropped the connection here; XploClone
        # answers the error and keeps the socket open.
        _, frames, done = _drain(ws, "Hello world.")
        assert len(frames) == 5
        assert done["type"] == "done"


def test_stream_non_object_json(client):
    with client.websocket_connect("/v1/tts/stream?key=test-key") as ws:
        ws.send_json(["not", "an", "object"])
        error = ws.receive_json()
        assert error["code"] == "bad_request"
        _, _, done = _drain(ws, "Hello world.")
        assert done["type"] == "done"


def test_stream_two_turns_one_socket(client):
    with client.websocket_connect("/v1/tts/stream?key=test-key") as ws:
        _, _, first = _drain(ws, "Hello world.")
        _, _, second = _drain(ws, "Hello again.")
        assert first["type"] == "done"
        assert second["type"] == "done"
        assert first["samples"] == second["samples"] == 800


# ── Review fixes (Claude Code review of PR #2, 2026-11-08) ──────────────────


def _recv_until_done(ws):
    start = ws.receive_json()
    frames = []
    while True:
        message = ws.receive()
        if message.get("bytes") is not None:
            frames.append(message["bytes"])
            continue
        import json

        return start, frames, json.loads(message["text"])


def test_stream_different_preset_is_not_served_from_cache(client, monkeypatch):
    from api.audio import sine_pcm16
    from api.engine import REGISTRY

    seen = []

    def one(voice_id, chunk, prosody=None):
        seen.append(prosody.preset)
        return sine_pcm16(0.1)

    monkeypatch.setattr(REGISTRY, "synthesize_one", one)
    with client.websocket_connect("/v1/tts/stream?key=test-key") as ws:
        for preset in ("natural", "firm"):
            ws.send_json({"voice_id": "mubashir-en-gb", "text": "Hello world.", "preset": preset})
            _recv_until_done(ws)
    assert seen == ["natural", "firm"]


def test_stream_cache_hit_reports_no_rtf(client):
    """A cache hit synthesised nothing: rtf is null and cache says hit,
    instead of a fake 'measured' rtf of 0.0."""
    with client.websocket_connect("/v1/tts/stream?key=test-key") as ws:
        ws.send_json({"voice_id": "mubashir-en-gb", "text": "Hello world."})
        _, frames1, first = _recv_until_done(ws)
        ws.send_json({"voice_id": "mubashir-en-gb", "text": "Hello world."})
        _, frames2, second = _recv_until_done(ws)
    assert first["cache"] == "miss" and isinstance(first["rtf"], float)
    assert second["cache"] == "hit" and second["rtf"] is None
    assert frames1 == frames2


def test_stream_client_hangup_is_not_a_synthesis_failure(client, monkeypatch):
    """A caller hanging up mid-stream used to be logged at ERROR, counted
    as 503 synthesis_failed, and then raise out of the handler."""
    import asyncio
    import json
    import time

    import api.main as main
    from api.audio import sine_pcm16
    from api.engine import REGISTRY
    from api.metrics import METRICS
    from api.rate_limit import SYNTHESIS_QUEUE

    def slow_one(voice_id, chunk, prosody=None):
        time.sleep(0.02)
        return sine_pcm16(0.1)

    monkeypatch.setattr(REGISTRY, "synthesize_one", slow_one)
    text = " ".join(f"Sentence number {i} is right here." for i in range(30))
    failed_before = METRICS.errors_total["mubashir-en-us:synthesis_failed"]
    hangups_before = METRICS.errors_total["mubashir-en-us:client_disconnected"]

    async def scenario():
        scope = {
            "type": "websocket",
            "path": "/v1/tts/stream",
            "raw_path": b"/v1/tts/stream",
            "query_string": b"key=test-key",
            "root_path": "",
            "scheme": "ws",
            "http_version": "1.1",
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 1),
            "subprotocols": [],
            "headers": [(b"host", b"testserver")],
        }
        request = json.dumps({"voice_id": "mubashir-en-us", "text": text})
        inbox = [
            {"type": "websocket.connect"},
            {"type": "websocket.receive", "text": request},
        ]
        gone = asyncio.Event()

        async def receive():
            if inbox:
                return inbox.pop(0)
            await gone.wait()
            return {"type": "websocket.disconnect", "code": 1006}

        frames = {"n": 0}

        async def send(message):
            if message.get("bytes"):
                frames["n"] += 1
                if frames["n"] > 3:  # caller hangs up after 3 frames
                    gone.set()
                    raise OSError("connection reset by peer")

        await main.app(scope, receive, send)  # must not raise
        await asyncio.sleep(0.05)
        return SYNTHESIS_QUEUE._sem.locked()

    assert asyncio.run(scenario()) is False
    assert METRICS.errors_total["mubashir-en-us:synthesis_failed"] == failed_before
    assert METRICS.errors_total["mubashir-en-us:client_disconnected"] == hangups_before + 1


def test_ws_accepts_bearer_header(client):
    headers = {"Authorization": "Bearer test-key"}
    with client.websocket_connect("/v1/tts/stream", headers=headers) as ws:
        ws.send_json({"voice_id": "nope", "text": "x"})
        assert ws.receive_json()["code"] == "unknown_voice"  # i.e. authorised


def test_ws_bad_bearer_header_rejected(client):
    headers = {"Authorization": "Bearer wrong"}
    with client.websocket_connect("/v1/tts/stream?key=test-key", headers=headers) as ws:
        assert ws.receive_json()["code"] == "unauthorized"  # header wins over query


def test_uvicorn_websocket_log_line_is_redacted():
    """uvicorn logs WebSocket paths with the query string; the ?key= value
    must never reach the log (verified live against uvicorn 0.54.0)."""
    import logging

    from api.logging_config import install_secret_redaction

    install_secret_redaction()
    record = logging.LogRecord(
        "uvicorn.error",
        logging.INFO,
        __file__,
        1,
        '%s - "WebSocket %s" [accepted]',
        ("127.0.0.1:5000", "/v1/tts/stream?key=SUPER-SECRET&x=1"),
        None,
    )
    for f in logging.getLogger("uvicorn.error").filters:
        f.filter(record)
    message = record.getMessage()
    assert "SUPER-SECRET" not in message
    assert "key=[REDACTED]&x=1" in message
