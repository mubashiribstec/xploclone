"""Tests for the provider-agnostic call session (api/telephony_session.py).

The engine is never touched here: rendering tests inject a fake
synthesizer (sine-tone PCM16 at 24 kHz) and stub the torchaudio
resample step, so the suite runs on CPU with no model and no torch.
The call-loop tests drive ``run_call`` with a fake WebSocket and a
fake provider adapter (no Twilio in Phase 1).
"""

from __future__ import annotations

import asyncio
import json

import numpy as np
import pytest

from api.audio import sine_pcm16
from api.chunking import chunk_text
from api.engine import EngineUnavailable
from api.telephony_audio import lin2ulaw
from api.telephony_session import (
    END_MARK,
    AnnouncementResponder,
    CallRecord,
    CallRegistry,
    CallTokens,
    Clear,
    Mark,
    SlidingWindow,
    StreamEvent,
    UlawCache,
    mask_call_id,
    registry,
    render_ulaw,
    render_ulaw_all,
    reset_state,
    run_call,
    token_subject,
    tokens,
)


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


async def _fake_synth(voice_id, chunks, prosody):
    for _ in chunks:
        yield sine_pcm16(0.1), 24000


class _CountingSynth:
    def __init__(self):
        self.calls: list[list[str]] = []

    async def __call__(self, voice_id, chunks, prosody):
        self.calls.append(list(chunks))
        async for item in _fake_synth(voice_id, chunks, prosody):
            yield item


async def _collect(text, **kwargs):
    return b"".join([chunk async for chunk in render_ulaw(text, **kwargs)])


# ── render_ulaw ─────────────────────────────────────────────────────────────


def test_render_ulaw_produces_8khz_ulaw():
    text = "Hello world."
    expected = fake_pcm16_to_ulaw(sine_pcm16(0.1), 24000) * len(chunk_text(text))
    out = asyncio.run(
        _collect(text, voice="mubashir-en-gb", language="en-GB", synthesizer=_fake_synth)
    )
    assert out == expected
    assert len(out) == 800 * len(chunk_text(text))  # 0.1 s of audio at 8 kHz


def test_render_ulaw_caches_repeat_render():
    synth = _CountingSynth()
    kwargs = {"voice": "mubashir-en-gb", "language": "en-GB", "synthesizer": synth}
    first = asyncio.run(_collect("Hello world.", **kwargs))
    second = asyncio.run(_collect("Hello world.", **kwargs))
    assert first == second
    assert len(synth.calls) == 1  # second render served from the greeting cache


def test_render_ulaw_single_flight():
    """Two concurrent renders of the same greeting share one synthesis."""
    synth = _CountingSynth()
    kwargs = {"voice": "mubashir-en-gb", "language": "en-GB", "synthesizer": synth}

    async def both():
        return await asyncio.gather(
            _collect("Hello world.", **kwargs), _collect("Hello world.", **kwargs)
        )

    a, b = asyncio.run(both())
    assert a == b
    assert len(synth.calls) == 1


def test_render_ulaw_empty_text_yields_nothing():
    synth = _CountingSynth()
    out = asyncio.run(_collect("", voice="mubashir-en-gb", synthesizer=synth))
    assert out == b""
    assert synth.calls == []


def test_render_ulaw_propagates_engine_error():
    async def bad_synth(voice_id, chunks, prosody):
        raise EngineUnavailable(voice_id, "engine is not loaded.")
        yield  # noqa: unreachable — makes this an async generator

    with pytest.raises(EngineUnavailable):
        asyncio.run(_collect("Hello world.", voice="mubashir-en-gb", synthesizer=bad_synth))


def test_render_ulaw_all_returns_bytes(monkeypatch):
    # render_ulaw_all uses the default synthesizer, so patch the module
    # global it resolves at call time.
    monkeypatch.setattr("api.telephony_session._xploclone_synthesizer", _fake_synth)
    out = asyncio.run(render_ulaw_all("Hello world.", voice="mubashir-en-gb", language="en-GB"))
    assert out == fake_pcm16_to_ulaw(sine_pcm16(0.1), 24000)


def test_announcement_responder_speaks(monkeypatch):
    monkeypatch.setattr("api.telephony_session._xploclone_synthesizer", _fake_synth)
    responder = AnnouncementResponder("Hello world.", voice="mubashir-en-gb", language="en-GB")

    async def collect():
        return b"".join([chunk async for chunk in responder.speak()])

    out = asyncio.run(collect())
    assert out == fake_pcm16_to_ulaw(sine_pcm16(0.1), 24000)
    assert asyncio.run(responder.on_inbound_audio(b"\xff" * 160)) is None


# ── Tokens, windows, registry, cache ────────────────────────────────────────


class _FakeClock:
    def __init__(self, now: float = 1000.0):
        self.now = now

    def __call__(self) -> float:
        return self.now


def test_call_tokens_single_use_and_binding():
    clock = _FakeClock()
    store = CallTokens(ttl_s=60.0, clock=clock)
    token = store.issue("call-1")
    assert token
    assert store.redeem(token, "call-1") is True
    assert store.redeem(token, "call-1") is False  # single use
    assert store.redeem(store.issue("call-2"), "wrong-call") is False


def test_call_tokens_expire():
    clock = _FakeClock()
    store = CallTokens(ttl_s=60.0, clock=clock)
    token = store.issue("call-1")
    clock.now += 61.0
    assert store.redeem(token, "call-1") is False


def test_call_tokens_epoch_blocks_stale_issue():
    clock = _FakeClock()
    store = CallTokens(clock=clock)
    assert store.issue("call-1", epoch=99) is None  # epoch 0 is current
    store.reset()  # epoch becomes 1
    assert store.issue("call-1", epoch=0) is None
    assert store.issue("call-1", epoch=1) is not None


def test_call_tokens_max_pending_evicts_oldest():
    store = CallTokens(max_pending=2, clock=_FakeClock())
    first = store.issue("call-a")
    store.issue("call-b")
    store.issue("call-c")
    assert store.pending() == 2
    assert store.redeem(first, "call-a") is False  # evicted


def test_sliding_window_allow_and_expiry():
    clock = _FakeClock()
    window = SlidingWindow(window_s=60.0, clock=clock)
    assert window.allow(2) is True
    assert window.allow(2) is True
    assert window.allow(2) is False
    assert window.exceeded(2) is True
    clock.now += 61.0
    assert window.allow(2) is True


def test_call_registry_capacity_and_snapshot():
    reg = CallRegistry()
    record = reg.begin("call-1", 1)
    assert isinstance(record, CallRecord)
    assert reg.begin("call-2", 1) is None  # full
    assert reg.has_capacity(1) is False
    assert reg.active() == 1
    reg.end(record, "completed")
    assert reg.active() == 0
    assert reg.has_capacity(1) is True
    snap = reg.snapshot()
    assert snap["recent"][0]["outcome"] == "completed"
    assert snap["recent"][0]["call"] == mask_call_id("call-1")


def test_ulaw_cache_lru_and_size_cap():
    cache = UlawCache(max_entries=2, max_bytes=10)
    cache.put(("a",), b"12345")
    cache.put(("b",), b"12345")
    cache.put(("c",), b"12345")  # 15 bytes > 10: oldest evicted
    assert cache.get(("a",)) is None
    assert cache.get(("b",)) == b"12345"
    cache.put(("big",), b"x" * 11)  # single value over the byte cap: ignored
    assert cache.get(("big",)) is None


def test_mask_call_id_and_token_subject():
    assert mask_call_id("abcdef") == "…cdef"
    assert mask_call_id("ab") == "…"
    assert token_subject("call-1") == "call-1"
    assert token_subject("call-1", "sess-9") == "call-1|sess-9"


def test_end_mark_renamed():
    assert END_MARK == "xploclone-end"


# ── run_call (fake provider + fake WebSocket) ───────────────────────────────


class FakeProvider:
    NAME = "fake"

    def parse_event(self, message):
        kind = message.get("type")
        if kind == "start":
            return StreamEvent(
                kind="start",
                stream_id=message.get("stream_id", "s1"),
                call_id=message.get("call_id", "call-1"),
                account_id=message.get("account_id", ""),
                params=message.get("params", {}),
            )
        if kind == "mark":
            return StreamEvent(kind="mark", mark=message.get("name", ""))
        if kind == "stop":
            return StreamEvent(kind="stop")
        if kind == "media":
            return StreamEvent(kind="media", payload=bytes.fromhex(message.get("payload", "")))
        return None

    def media_message(self, stream_id, payload):
        return {"type": "media", "stream_id": stream_id, "payload": payload.hex()}

    def mark_message(self, stream_id, name):
        return {"type": "mark", "stream_id": stream_id, "name": name}

    def clear_message(self, stream_id):
        return {"type": "clear", "stream_id": stream_id}


class FakeWebSocket:
    """Scripted receive_text; "<wait-end-mark:X>" waits until the
    END_MARK is in the sent log, then delivers event X (mark/stop)."""

    def __init__(self, messages):
        self._messages = list(messages)
        self._next = 0
        self.sent: list[dict] = []
        self.accepted = False
        self.close_code: int | None = None

    async def accept(self):
        self.accepted = True

    async def receive_text(self):
        if self._next < len(self._messages):
            msg = self._messages[self._next]
            self._next += 1
            if isinstance(msg, str) and msg.startswith("<wait-end-mark:"):
                want = msg[len("<wait-end-mark:") : -1]
                for _ in range(400):
                    if any(
                        m.get("type") == "mark" and m.get("name") == END_MARK for m in self.sent
                    ):
                        break
                    await asyncio.sleep(0.005)
                if want == "mark":
                    return json.dumps({"type": "mark", "name": END_MARK})
                return json.dumps({"type": "stop"})
            return msg
        await asyncio.sleep(30)
        from starlette.websockets import WebSocketDisconnect

        raise WebSocketDisconnect()

    async def send_json(self, message):
        self.sent.append(message)

    async def close(self, code=1000):
        self.close_code = code


class FakeResponder:
    def __init__(self, chunks):
        self._chunks = list(chunks)
        self.heard: list[bytes] = []

    def speak(self):
        async def _gen():
            for chunk in self._chunks:
                yield chunk

        return _gen()

    async def on_inbound_audio(self, ulaw):
        self.heard.append(ulaw)


def _start_message(token, account_id="acct-1", call_id="call-1"):
    return json.dumps(
        {
            "type": "start",
            "stream_id": "s1",
            "call_id": call_id,
            "account_id": account_id,
            "params": {"token": token},
        }
    )


def _run(ws, factory, max_seconds=5.0, max_calls=1):
    return asyncio.run(
        run_call(
            ws,
            FakeProvider(),
            account_id="acct-1",
            responder_factory=factory,
            max_calls=max_calls,
            max_seconds=max_seconds,
        )
    )


def test_run_call_rejects_missing_token():
    ws = FakeWebSocket(
        [json.dumps({"type": "start", "call_id": "call-1", "account_id": "acct-1", "params": {}})]
    )
    outcome = _run(ws, lambda start: FakeResponder([b"\xff" * 160]))
    assert outcome == "rejected_stream"
    assert ws.close_code == 1008
    assert ws.accepted is True


def test_run_call_rejects_wrong_account():
    token = tokens.issue("call-1")
    ws = FakeWebSocket([_start_message(token, account_id="someone-else")])
    outcome = _run(ws, lambda start: FakeResponder([b"\xff" * 160]))
    assert outcome == "rejected_stream"
    assert ws.close_code == 1008


def test_run_call_refused_by_factory():
    token = tokens.issue("call-1")
    ws = FakeWebSocket([_start_message(token)])
    outcome = _run(ws, lambda start: None)
    assert outcome == "rejected_stream"
    assert ws.close_code == 1008
    assert registry.active() == 0


def test_run_call_busy_when_registry_full():
    token = tokens.issue("call-1")
    existing = registry.begin("other-call", 1)
    assert existing is not None
    ws = FakeWebSocket([_start_message(token)])
    outcome = _run(ws, lambda start: FakeResponder([b"\xff" * 160]), max_calls=1)
    assert outcome == "busy"
    assert ws.close_code == 1013
    registry.end(existing, "completed")  # tidy up the pre-filled slot


def test_run_call_completed_and_frames_are_160_bytes():
    token = tokens.issue("call-1")
    ws = FakeWebSocket([_start_message(token), "<wait-end-mark:mark>"])
    outcome = _run(ws, lambda start: FakeResponder([b"\xff" * 320]))
    assert outcome == "completed"
    assert ws.close_code == 1000
    kinds = [m["type"] for m in ws.sent]
    assert kinds == ["media", "media", "mark"]  # 2 frames, then the end mark
    assert all(len(bytes.fromhex(m["payload"])) == 160 for m in ws.sent if m["type"] == "media")
    assert ws.sent[-1] == {"type": "mark", "stream_id": "s1", "name": END_MARK}
    snap = registry.snapshot()
    assert snap["recent"][0]["outcome"] == "completed"
    assert snap["recent"][0]["audio_seconds"] == pytest.approx(0.04)  # 320 bytes / 8000


def test_run_call_caller_hangs_up():
    token = tokens.issue("call-1")
    ws = FakeWebSocket([_start_message(token), json.dumps({"type": "stop"})])
    outcome = _run(ws, lambda start: FakeResponder([b"\xff" * 160]))
    assert outcome == "caller_hung_up"
    assert ws.close_code == 1000


def test_run_call_clear_and_mark_flow():
    token = tokens.issue("call-1")
    ws = FakeWebSocket([_start_message(token), "<wait-end-mark:stop>"])
    chunks = [b"\x01" * 320, Mark("m1"), Clear(), b"\x02" * 160]
    outcome = _run(ws, lambda start: FakeResponder(chunks))
    assert outcome == "caller_hung_up"
    kinds = [(m["type"], m.get("name")) for m in ws.sent]
    assert kinds == [
        ("media", None),
        ("media", None),
        ("mark", "m1"),
        ("clear", None),
        ("media", None),
        ("mark", END_MARK),
    ]
    media = [bytes.fromhex(m["payload"]) for m in ws.sent if m["type"] == "media"]
    assert media[0] == b"\x01" * 160 and media[1] == b"\x01" * 160
    assert media[2] == b"\x02" * 160


def test_run_call_time_limit():
    class SlowResponder:
        def speak(self):
            async def _gen():
                while True:
                    yield b"\xff" * 160
                    await asyncio.sleep(0.5)

            return _gen()

        async def on_inbound_audio(self, ulaw):
            return None

    token = tokens.issue("call-1")
    ws = FakeWebSocket([_start_message(token)])
    outcome = _run(ws, lambda start: SlowResponder(), max_seconds=0.05)
    assert outcome == "time_limit"
    assert ws.close_code == 1000
