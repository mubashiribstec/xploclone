"""Streaming TTS over WebSocket — 8 kHz μ-law for phone lines (Phase 1).

Adapted from VoiceStudio (debpalash/VoiceStudio,
``backend/api/routers/tts_stream.py``, AGPL-3.0-only) into XploClone,
a private personal-learning repo. The protocol shape is VoiceStudio's
(start frame, binary audio frames, done frame with measured TTFA);
everything else is XploClone's own engine, voices and error contract.

Protocol (one JSON request per turn; the socket stays open for the
next request):
    → Client sends JSON: {"voice_id": "mubashir-en-gb", "text": "...",
      "preset": "natural", ...}   (auth: ``?key=<api-key>`` in the URL)
    ← Server sends JSON: {"type": "start", "sample_rate": 8000,
      "channels": 1, "format": "ulaw", "engine": "chatterbox-turbo",
      "voice": "mubashir-en-gb"}
    ← Server sends binary μ-law frames, 160 bytes (20 ms) each
    ← Server sends JSON: {"type": "done", "duration_s": 4.2,
      "gen_time_s": 1.1, "ttfa_ms": 180.0, "rtf": 0.262,
      "samples": 33600, "sample_rate": 8000, "format": "ulaw",
      "engine": "chatterbox-turbo", "voice": "mubashir-en-gb",
      "watermark": "perth-unverified"}
    ← Server sends JSON: {"type": "error", "code": "...", "detail": "..."}

TTFA is measured honestly: from the request arriving to the first
audio frame handed to the socket. RTF is synthesis seconds per audio
second (per-sentence synthesis time only — never wall clock, which
would blame the engine for a slow client).

Audit fixes vs the VoiceStudio original (full list in
``docs/TELEPHONY-PORT-PHASE1.md``):
- Output is 8 kHz μ-law in 20 ms frames, not 24 kHz PCM16 in 200 ms
  chunks — this endpoint speaks the phone line, not the browser.
- The socket requires the API key (``?key=``), constant-time
  compared like ``POST /v1/tts``. VoiceStudio's route had no auth
  check of its own (local desktop app); an unauthenticated XploClone
  socket would bypass the Bearer auth of ``/v1/tts``.
- Text is capped at ``SETTINGS.max_chars`` (5,000, same as
  ``/v1/tts``) and must be a string; the original accepted any
  length and any JSON type.
- A malformed JSON message gets an error frame and the socket stays
  open; the original dropped the connection on any receive error.
- Unknown voice and Urdu are errors, never a silent fallback to
  another voice (XploClone's standing rule). The original resolved
  any voice string through a profile DB.
- The synthesis queue is shared with ``POST /v1/tts`` (one
  concurrent synthesis — see ``api/rate_limit.py``); the original
  used a GPU-pool guard XploClone does not have.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import time
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .audio import SAMPLE_RATE
from .auth import hash_key
from .config import SETTINGS
from .engine import REGISTRY, EngineUnavailable
from .logging_config import logger
from .metrics import METRICS
from .normalize import apply_tag_policy, humanize_text, normalize_text
from .prosody import ProsodySettings, resolve_prosody
from .rate_limit import RATE_LIMITER, SYNTHESIS_QUEUE
from .telephony_audio import FRAME_BYTES, PHONE_SAMPLE_RATE, ULAW_SILENCE
from .telephony_session import render_ulaw
from .voices import get_voice

router = APIRouter()


def _ws_authorized(websocket: WebSocket) -> tuple[bool, str | None]:
    """(authorized, error_code). Mirrors ``api/auth.py`` require_api_key.

    WebSockets cannot carry an Authorization header from a browser, so
    the key travels as a ``?key=`` query parameter and is compared in
    constant time against the stored hash — never logged, never echoed.
    """
    if not SETTINGS.api_key_hash and SETTINGS.allow_no_auth:
        return True, None
    if not SETTINGS.api_key_hash:
        return False, "auth_not_configured"
    token = websocket.query_params.get("key")
    if token is None or not hmac.compare_digest(hash_key(token), SETTINGS.api_key_hash):
        return False, "unauthorized"
    return True, None


async def _timed_synthesizer(
    voice_id: str,
    chunks: list[str],
    prosody: ProsodySettings,
    synth_times: list[float],
) -> AsyncIterator[tuple[bytes, int]]:
    """Chatterbox Turbo, one chunk at a time, timing pure synthesis.

    Identical to the session module's default synthesizer except that
    each chunk's synthesis seconds are recorded, so the done frame can
    report a true RTF (synthesis seconds per audio second) instead of
    a wall-clock ratio.
    """
    await asyncio.to_thread(REGISTRY.ensure_loaded, voice_id)
    for chunk in chunks:
        started = time.perf_counter()
        pcm = await asyncio.to_thread(REGISTRY.synthesize_one, voice_id, chunk, prosody)
        synth_times.append(time.perf_counter() - started)
        yield pcm, SAMPLE_RATE


async def _handle_stream_request(
    websocket: WebSocket, data: Any, token: str
) -> None:
    """One request on an already-authenticated socket."""
    t0 = time.perf_counter()
    if not isinstance(data, dict):
        await websocket.send_json(
            {"type": "error", "code": "bad_request", "detail": "Request must be a JSON object."}
        )
        return
    text = data.get("text")
    if not isinstance(text, str) or not text.strip():
        await websocket.send_json(
            {"type": "error", "code": "empty_text", "detail": "Text must be a non-empty string."}
        )
        return
    voice_id = data.get("voice_id")
    if not isinstance(voice_id, str) or get_voice(voice_id) is None:
        await websocket.send_json(
            {
                "type": "error",
                "code": "unknown_voice",
                "detail": "Unknown voice_id. Valid voices: mubashir-en-us, mubashir-en-gb, mubashir-ur.",
            }
        )
        return
    # Voice is checked before length (unlike POST /v1/tts) so the
    # text_too_long metric below always has a known voice_id.
    if len(text) > SETTINGS.max_chars:
        METRICS.record(voice_id, "400", 0.0, error_code="text_too_long")
        await websocket.send_json(
            {
                "type": "error",
                "code": "text_too_long",
                "detail": f"Text exceeds {SETTINGS.max_chars} characters.",
            }
        )
        return
    try:
        prosody = resolve_prosody(
            preset=data.get("preset"),
            style=data.get("style"),
            exaggeration=data.get("exaggeration"),
            cfg_weight=data.get("cfg_weight"),
            temperature=data.get("temperature"),
            top_p=data.get("top_p"),
            repetition_penalty=data.get("repetition_penalty"),
        )
    except (ValueError, TypeError) as exc:
        METRICS.record(voice_id, "400", 0.0, error_code="invalid_preset")
        await websocket.send_json(
            {"type": "error", "code": "invalid_preset", "detail": str(exc)}
        )
        return
    allowed, retry_after = RATE_LIMITER.allow(hash_key(token))
    if not allowed:
        METRICS.record(voice_id, "429", 0.0, error_code="rate_limited")
        await websocket.send_json(
            {
                "type": "error",
                "code": "rate_limited",
                "detail": "Rate limit exceeded (60 req/min per key).",
                "retry_after": retry_after,
            }
        )
        return
    # Text pipeline (same order as POST /v1/tts): tag policy first,
    # then normalisation, then humanise. Normalised exactly once, on
    # the whole text, before chunking (render_ulaw chunks it).
    norm = humanize_text(normalize_text(apply_tag_policy(text, allow_tags=True)))
    if not norm:
        await websocket.send_json(
            {"type": "error", "code": "empty_text", "detail": "Text is empty after normalisation."}
        )
        return
    voice = get_voice(voice_id)
    assert voice is not None  # checked above; keeps mypy honest below
    acquired = await SYNTHESIS_QUEUE.acquire()
    if not acquired:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        METRICS.record(voice_id, "503", latency_ms, error_code="engine_busy")
        await websocket.send_json(
            {
                "type": "error",
                "code": "engine_busy",
                "detail": "Synthesis queue is full or timed out. Retry shortly.",
                "retry_after": 5,
            }
        )
        return
    synth_times: list[float] = []
    try:
        # Validate the engine BEFORE any audio is framed, mirroring the
        # pcm16 path in POST /v1/tts.
        try:
            await asyncio.to_thread(REGISTRY.ensure_loaded, voice_id)
        except EngineUnavailable as exc:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            METRICS.record(voice_id, "503", latency_ms, error_code=exc.code)
            await websocket.send_json(
                {"type": "error", "code": exc.code, "detail": exc.reason}
            )
            return

        async def synthesizer(
            vid: str, chunks: list[str], pros: ProsodySettings
        ) -> AsyncIterator[tuple[bytes, int]]:
            async for item in _timed_synthesizer(vid, chunks, pros, synth_times):
                yield item

        started = False
        first_audio_at: float | None = None
        sent_bytes = 0
        frames_sent = 0
        pending = b""
        try:
            async for ulaw in render_ulaw(
                norm, voice=voice_id, language=voice.language, prosody=prosody,
                synthesizer=synthesizer,
            ):
                if not started:
                    await websocket.send_json(
                        {
                            "type": "start",
                            "sample_rate": PHONE_SAMPLE_RATE,
                            "channels": 1,
                            "format": "ulaw",
                            "engine": REGISTRY.engine_name,
                            "voice": voice_id,
                        }
                    )
                    started = True
                pending += ulaw
                whole = len(pending) - len(pending) % FRAME_BYTES
                for i in range(0, whole, FRAME_BYTES):
                    await websocket.send_bytes(pending[i : i + FRAME_BYTES])
                    if first_audio_at is None:
                        # TTFA ends when the first audio bytes have been
                        # handed to the socket.
                        first_audio_at = time.perf_counter()
                    sent_bytes += FRAME_BYTES
                    frames_sent += 1
                    if frames_sent % 50 == 0:
                        await asyncio.sleep(0)  # keep the receive side responsive
                pending = pending[whole:]
            if pending:
                frame = pending + bytes([ULAW_SILENCE]) * (FRAME_BYTES - len(pending))
                await websocket.send_bytes(frame)
                if first_audio_at is None:
                    first_audio_at = time.perf_counter()
                sent_bytes += FRAME_BYTES
        except EngineUnavailable as exc:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            METRICS.record(voice_id, "503", latency_ms, error_code=exc.code)
            await websocket.send_json(
                {"type": "error", "code": exc.code, "detail": exc.reason}
            )
            return
        except Exception as exc:  # noqa: BLE001 — m10: never leak a stack trace
            latency_ms = (time.perf_counter() - t0) * 1000.0
            METRICS.record(voice_id, "503", latency_ms, error_code="synthesis_failed")
            logger.error(
                "streaming synthesis failed",
                extra={
                    "fields": {
                        "voice_id": voice_id,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                },
            )
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "synthesis_failed",
                    "detail": "Synthesis failed. Try again shortly.",
                }
            )
            return

        finished_at = time.perf_counter()
        duration = round(sent_bytes / PHONE_SAMPLE_RATE, 3)
        ttfa_ms = (
            round(max(0.0, first_audio_at - t0) * 1000.0, 1)
            if first_audio_at is not None
            else None
        )
        synth_time = sum(synth_times)
        rtf = round(synth_time / duration, 3) if duration > 0 else None
        latency_ms = (finished_at - t0) * 1000.0
        METRICS.record(voice_id, "200", latency_ms, chars=len(text))
        logger.info(
            "tts stream",
            extra={
                "fields": {
                    "voice_id": voice_id,
                    "chars": len(text),
                    "duration_s": duration,
                    "latency_ms": round(latency_ms, 1),
                    "ttfa_ms": ttfa_ms,
                    "rtf": rtf,
                    "watermark": "perth-unverified",
                    "preset": prosody.preset,
                }
            },
        )
        await websocket.send_json(
            {
                "type": "done",
                "duration_s": duration,
                # Microsecond precision, not the 1 ms of the original:
                # with 3 decimals a fast render rounded gen_time_s
                # below ttfa_ms, which is impossible (TTFA is measured
                # inside the same interval) and looked like a bug.
                "gen_time_s": round(finished_at - t0, 6),
                "ttfa_ms": ttfa_ms,
                "rtf": rtf,
                "samples": sent_bytes,
                "sample_rate": PHONE_SAMPLE_RATE,
                "format": "ulaw",
                "engine": REGISTRY.engine_name,
                "voice": voice_id,
                "watermark": "perth-unverified",
            }
        )
    finally:
        SYNTHESIS_QUEUE.release()


@router.websocket("/v1/tts/stream")
async def ws_tts_stream(websocket: WebSocket) -> None:
    """Stream TTS audio over WebSocket (μ-law, 8 kHz, 20 ms frames).

    The client sends one JSON request per turn, then receives a start
    frame, binary μ-law frames and a done frame. The connection stays
    open for subsequent requests (conversational mode).
    """
    await websocket.accept()
    authorized, auth_error = _ws_authorized(websocket)
    if not authorized:
        detail = (
            "No API key is configured on this server."
            if auth_error == "auth_not_configured"
            else "Invalid or missing API key."
        )
        await websocket.send_json({"type": "error", "code": auth_error, "detail": detail})
        await websocket.close(code=1008)
        return
    token = websocket.query_params.get("key") or ""
    logger.info("TTS stream WebSocket connected", extra={"fields": {}})

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                break
            except Exception:
                # Malformed JSON (or a binary frame): tell the client
                # and keep the socket open for the next request. The
                # VoiceStudio original dropped the connection here.
                try:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "code": "bad_request",
                            "detail": "Request must be a JSON object.",
                        }
                    )
                except WebSocketDisconnect:
                    break
                continue
            try:
                await _handle_stream_request(websocket, data, token)
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        pass
    finally:
        logger.info("TTS stream WebSocket disconnected", extra={"fields": {}})
