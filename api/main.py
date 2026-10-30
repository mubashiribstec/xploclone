"""XploClone API — FastAPI, Phase 1 (English MVP).

Endpoints (PLAN-v2 §6.1):
- GET  /health      — liveness + engine status. Public.
- GET  /metrics     — Prometheus text. Public (no secrets in it).
- GET  /v1/voices   — the 3 hardcoded voices with loaded/unavailable. Public.
- POST /v1/tts      — Bearer API key required. Streams 24 kHz WAV.

Error contract (never silent fallback):
- 400 unknown voice_id / text empty / text > 5000 chars / bad format.
- 401 invalid or missing API key.
- 429 rate limit exceeded (Retry-After header).
- 503 engine_unavailable (Urdu, or English engine/reference missing),
  engine_busy (queue full / timeout, Retry-After header),
  auth_not_configured (no key hash set and dev mode off).

Live-call WebSocket streaming, fine-tuning, and hardening are NOT in
this build (Phase 3/4/5) — see README "Not built yet".
"""

from __future__ import annotations

import hashlib
import time
import uuid
from collections.abc import Iterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from .audio import SAMPLE_RATE, pcm16_to_wav
from .auth import require_api_key
from .chunking import chunk_text
from .config import SETTINGS
from .engine import REGISTRY, EngineUnavailable
from .logging_config import logger
from .metrics import METRICS
from .normalize import normalize_text
from .rate_limit import RateLimiter, SynthesisQueue
from .voices import VOICES, get_voice

app = FastAPI(
    title="XploClone API",
    version="0.1.0",
    description="Single-owner voice-cloning TTS — Mubashir Ali's voice only. Phase 1: English MVP.",
)
rate_limiter = RateLimiter(per_min=SETTINGS.rate_limit_per_min)
synthesis_queue = SynthesisQueue(
    max_waiters=SETTINGS.queue_max, timeout_s=float(SETTINGS.request_timeout_s)
)


class TTSRequest(BaseModel):
    voice_id: str = Field(..., description="One of mubashir-en-us, mubashir-en-gb, mubashir-ur")
    text: str = Field(..., min_length=1, max_length=5000)
    format: str = Field("wav", description="wav | pcm16 (mp3 is not supported in v1)")


@app.middleware("http")
async def request_logging(request: Request, call_next):  # type: ignore[no-untyped-def]
    request_id = str(uuid.uuid4())[:8]
    started = time.monotonic()
    response = await call_next(request)
    latency_ms = (time.monotonic() - started) * 1000.0
    # Never log text content, audio, or API keys — only metadata.
    logger.info(
        "request",
        extra={
            "fields": {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "latency_ms": round(latency_ms, 1),
            }
        },
    )
    response.headers["X-Request-Id"] = request_id
    return response


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "version": "0.1.0",
        "engines": {
            "en": "loaded" if REGISTRY.status("mubashir-en-us") == "loaded" else "unavailable",
            "ur": "unavailable",
        },
        "voices": {v.voice_id: REGISTRY.status(v.voice_id) for v in VOICES},
        "device": SETTINGS.device,
        "chatterbox_revision": SETTINGS.chatterbox_revision,
    }


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    return METRICS.render_prometheus()


@app.get("/v1/voices")
def list_voices() -> dict[str, object]:
    return {
        "voices": [
            {
                "voice_id": v.voice_id,
                "language": v.language,
                "accent": v.accent,
                "engine": v.engine,
                "status": REGISTRY.status(v.voice_id),
                "description": v.description,
            }
            for v in VOICES
        ]
    }


@app.post("/v1/tts")
async def text_to_speech(payload: TTSRequest, request: Request):  # type: ignore[no-untyped-def]
    started = time.monotonic()
    voice = get_voice(payload.voice_id)
    if voice is None:
        METRICS.record(payload.voice_id, "400", 0.0, error_code="unknown_voice")
        raise HTTPException(
            status_code=400,
            detail={
                "code": "unknown_voice",
                "message": f"Unknown voice_id: {payload.voice_id}. "
                "Valid voices: mubashir-en-us, mubashir-en-gb, mubashir-ur.",
            },
        )
    if payload.format not in ("wav", "pcm16"):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "unsupported_format",
                "message": "format must be 'wav' or 'pcm16'. MP3 is not supported in v1.",
            },
        )
    require_api_key(request)
    key_hash = hashlib.sha256((request.headers.get("Authorization", "")).encode()).hexdigest()
    allowed, retry_after = rate_limiter.allow(key_hash)
    if not allowed:
        METRICS.record(payload.voice_id, "429", 0.0, error_code="rate_limited")
        return JSONResponse(
            status_code=429,
            content={
                "detail": {
                    "code": "rate_limited",
                    "message": "Rate limit exceeded (60 req/min per key).",
                }
            },
            headers={"Retry-After": str(retry_after)},
        )

    text = normalize_text(payload.text)
    if not text:
        raise HTTPException(
            status_code=400,
            detail={"code": "empty_text", "message": "Text is empty after normalisation."},
        )
    chunks = chunk_text(text)
    acquired = await synthesis_queue.acquire()
    if not acquired:
        latency = (time.monotonic() - started) * 1000.0
        METRICS.record(payload.voice_id, "503", latency, error_code="engine_busy")
        return JSONResponse(
            status_code=503,
            content={
                "detail": {
                    "code": "engine_busy",
                    "message": "Synthesis queue is full or timed out. Retry shortly.",
                }
            },
            headers={"Retry-After": "5"},
        )
    try:
        result = REGISTRY.synthesize(payload.voice_id, chunks)
    except EngineUnavailable as exc:
        latency = (time.monotonic() - started) * 1000.0
        METRICS.record(payload.voice_id, "503", latency, error_code=exc.code)
        raise HTTPException(
            status_code=503,
            detail={"code": exc.code, "message": exc.reason},
        ) from exc
    finally:
        synthesis_queue.release()

    latency_ms = (time.monotonic() - started) * 1000.0
    METRICS.record(payload.voice_id, "200", latency_ms, chars=len(payload.text))
    logger.info(
        "tts",
        extra={
            "fields": {
                "voice_id": payload.voice_id,
                "chars": len(payload.text),
                "chunks": result.chunks,
                "latency_ms": round(latency_ms, 1),
                "engine_latency_ms": round(result.latency_ms, 1),
                "watermark": result.watermark,
            }
        },
    )
    if payload.format == "pcm16":
        body = result.pcm16
        media_type = "audio/L16; rate=24000"
    else:
        body = pcm16_to_wav(result.pcm16, SAMPLE_RATE)
        media_type = "audio/wav"

    def _stream() -> Iterator[bytes]:
        yield body

    return StreamingResponse(
        _stream(),
        media_type=media_type,
        headers={
            "X-XploClone-Voice": payload.voice_id,
            "X-XploClone-Chars": str(len(payload.text)),
            "X-XploClone-Latency-Ms": f"{latency_ms:.1f}",
            "X-Watermark": result.watermark,
            "Content-Disposition": f'attachment; filename="xploclone-{payload.voice_id}.wav"',
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):  # type: ignore[no-untyped-def]
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
