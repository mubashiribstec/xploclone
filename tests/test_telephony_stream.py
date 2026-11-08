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
