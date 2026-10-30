"""XploClone API — FastAPI, Phase 1 (English MVP).

Endpoints (PLAN-v2 §6.1):
- GET  /health      — liveness + readiness + engine status. Public.
- GET  /metrics     — Prometheus text. Public (no secrets in it).
- GET  /v1/voices   — the 3 hardcoded voices with loaded/unavailable. Public.
- POST /v1/tts      — Bearer API key required. Streams 24 kHz WAV.

Error contract (never silent fallback):
- 400 unknown voice_id / text empty / text > max chars / bad format /
  unknown preset (invalid_preset). 422 out-of-range prosody knob.
- 401 invalid or missing API key.
- 429 rate limit exceeded (Retry-After header).
- 503 engine_unavailable (Urdu, or English engine/reference missing),
  engine_busy (queue full / timeout, Retry-After header),
  auth_not_configured (no key hash set and dev mode off),
  synthesis_failed (unexpected synthesis error — generic message only).

Synthesis runs off the event loop (M2): ``REGISTRY.synthesize`` is
blocking GPU work, so it is executed via ``asyncio.to_thread`` — a long
generation must not stall ``/health`` or other requests.

Live-call WebSocket streaming, fine-tuning, and hardening are NOT in
this build (Phase 3/4/5) — see README "Not built yet".
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from .audio import SAMPLE_RATE, pcm16_to_wav
from .auth import bearer_token, hash_key, require_api_key
from .cache import AudioCache
from .chunking import chunk_text
from .config import SETTINGS
from .engine import REGISTRY, EngineUnavailable
from .logging_config import logger
from .metrics import METRICS
from .normalize import apply_tag_policy, humanize_text, normalize_text
from .prosody import (
    TURBO_CFG_EFFECTIVE,
    TURBO_EXAGGERATION_EFFECTIVE,
    ProsodySettings,
    resolve_prosody,
)
from .rate_limit import RateLimiter, SynthesisQueue
from .voices import VOICES, get_voice


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Optional startup warmup (m7): load the engine so /health reports
    # readiness and the first request does not pay the full load time.
    # Off by default — CPU-only smoke tests start fast.
    if SETTINGS.warmup_on_startup:
        await asyncio.to_thread(REGISTRY.warmup)
    yield


app = FastAPI(
    title="XploClone API",
    version="0.1.0",
    description="Single-owner voice-cloning TTS — Mubashir Ali's voice only. Phase 1: English MVP.",
    lifespan=lifespan,
)
# Same-origin via the Next.js proxy only (m17). Direct browser calls are
# not supported and no CORS middleware is enabled.
app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(SETTINGS.allowed_hosts))

rate_limiter = RateLimiter(per_min=SETTINGS.rate_limit_per_min)
# Coarse per-IP limiter, applied BEFORE auth (m5): unauthenticated
# requests must not be able to flood the 401 path for free.
ip_limiter = RateLimiter(per_min=120)
synthesis_queue = SynthesisQueue(
    max_waiters=SETTINGS.queue_max, timeout_s=float(SETTINGS.request_timeout_s)
)
# Identical-request audio cache (in-memory, per process). Keyed by
# (voice_id, normalised text, format, prosody); see api/cache.py.
AUDIO_CACHE = AudioCache(ttl_s=SETTINGS.cache_ttl_s, max_entries=SETTINGS.cache_max_entries)


class TTSRequest(BaseModel):
    voice_id: str = Field(..., description="One of mubashir-en-us, mubashir-en-gb, mubashir-ur")
    # No max_length here: over-long text is a 400 (m1), not Pydantic's 422.
    # The limit is enforced in the endpoint from SETTINGS.max_chars (m6).
    text: str = Field(..., min_length=1)
    format: str = Field("wav", description="wav | pcm16 (mp3 is not supported in v1)")
    # Prosody (human-voice work, 2026-10-30 — see api/prosody.py).
    # preset: default | natural | warm | firm. style is an alias for
    # preset (either may be sent, not two different values). Explicit
    # knobs override the preset. exaggeration / cfg_weight are
    # accepted, validated and logged, but Turbo 0.1.7 IGNORES them —
    # the audible variation comes from temperature / top_p /
    # repetition_penalty. Response headers report that honestly.
    # Out-of-range knobs are Pydantic 422s; unknown preset is 400
    # invalid_preset (resolved in the endpoint, not by Pydantic).
    preset: str | None = Field(None, description="default | natural | warm | firm")
    style: str | None = Field(None, description="Alias for preset (deprecated, use preset)")
    exaggeration: float | None = Field(None, ge=0.0, le=1.0)
    cfg_weight: float | None = Field(None, ge=0.0, le=1.0)
    temperature: float | None = Field(None, ge=0.1, le=1.5)
    top_p: float | None = Field(None, ge=0.05, le=1.0)
    repetition_penalty: float | None = Field(None, ge=1.0, le=2.0)


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
    # Liveness is always "ok" (m7): this endpoint must answer even while
    # a synthesis is running. Readiness is separate — the engine may
    # legitimately be "not ready" until warmup / the first load.
    ready = (
        REGISTRY.status("mubashir-en-us") == "loaded"
        or REGISTRY.status("mubashir-en-gb") == "loaded"
    )
    return {
        "status": "ok",
        "ready": ready,
        "version": "0.1.0",
        "engines": {
            "en": "loaded" if ready else "unavailable",
            "ur": "unavailable",
        },
        "voices": {v.voice_id: REGISTRY.status(v.voice_id) for v in VOICES},
        "device": SETTINGS.device,
        "engine": SETTINGS.engine,
        "engine_name": REGISTRY.engine_name,
        "chatterbox_revision": SETTINGS.chatterbox_revision,
        "chatterbox_revision_resolved": REGISTRY.resolved_revision,
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
    # Per-IP limit before auth (m5).
    client_ip = request.client.host if request.client else "unknown"
    ip_allowed, ip_retry = ip_limiter.allow(f"ip:{client_ip}")
    if not ip_allowed:
        return JSONResponse(
            status_code=429,
            content={
                "detail": {"code": "rate_limited", "message": "Too many requests from this IP."}
            },
            headers={"Retry-After": str(ip_retry)},
        )
    if len(payload.text) > SETTINGS.max_chars:
        METRICS.record(payload.voice_id, "400", 0.0, error_code="text_too_long")
        raise HTTPException(
            status_code=400,
            detail={
                "code": "text_too_long",
                "message": f"Text exceeds {SETTINGS.max_chars} characters.",
            },
        )
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
    # Prosody resolution: unknown preset / conflicting preset+style /
    # out-of-range knob (only reachable if Pydantic was bypassed) is a
    # 400 invalid_preset — never a 500, never a silent default.
    try:
        prosody = resolve_prosody(
            preset=payload.preset,
            style=payload.style,
            exaggeration=payload.exaggeration,
            cfg_weight=payload.cfg_weight,
            temperature=payload.temperature,
            top_p=payload.top_p,
            repetition_penalty=payload.repetition_penalty,
        )
    except ValueError as exc:
        METRICS.record(payload.voice_id, "400", 0.0, error_code="invalid_preset")
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_preset", "message": str(exc)},
        ) from exc
    require_api_key(request)
    # Rate-limit on the token hash (m5) — not on the full "Bearer …"
    # header, so "Bearer" vs "bearer" spellings share one bucket.
    token = bearer_token(request) or ""
    allowed, retry_after = rate_limiter.allow(hash_key(token))
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

    # Text pipeline (order matters): tag policy FIRST (raw text may
    # contain [laugh] etc. — whitelist for file generation, strip the
    # rest), then normalisation (numbers/dates/postcodes), then
    # humanize (line breaks -> sentence breaks, long sentences split).
    # humanize only inserts punctuation breaks; the words are unchanged.
    text = humanize_text(normalize_text(apply_tag_policy(payload.text, allow_tags=True)))
    if not text:
        raise HTTPException(
            status_code=400,
            detail={"code": "empty_text", "message": "Text is empty after normalisation."},
        )
    chunks = chunk_text(text)
    # Identical-request cache: the cache stores PCM16; WAV is wrapped
    # from it on a hit. Cache key uses normalised text, so "Hello." and
    # "hello." (same after normalisation) share one entry — AND the
    # prosody fragment, so a "natural" request never gets a cached
    # "default" take.
    cache_key = AudioCache.key(payload.voice_id, text, payload.format, prosody.cache_fragment())
    cached_pcm = AUDIO_CACHE.get(cache_key)
    METRICS.record_cache(cached_pcm is not None)
    if cached_pcm is not None:
        latency_ms = (time.monotonic() - started) * 1000.0
        METRICS.record(payload.voice_id, "200", latency_ms, chars=len(payload.text))
        logger.info(
            "tts",
            extra={
                "fields": {
                    "voice_id": payload.voice_id,
                    "chars": len(payload.text),
                    "chunks": len(chunks),
                    "latency_ms": round(latency_ms, 1),
                    "cache": "hit",
                    "watermark": "perth-unverified",
                    "preset": prosody.preset,
                    "exaggeration": prosody.exaggeration,
                    "cfg_weight": prosody.cfg_weight,
                    "temperature": prosody.temperature,
                }
            },
        )
        return _audio_response(payload, cached_pcm, latency_ms, cache="hit", prosody=prosody)
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
    # Per-sentence streaming (pcm16 only): validate the engine BEFORE
    # headers are sent, then stream chunk-by-chunk. WAV stays whole-file
    # because its header needs the total size up front.
    if payload.format == "pcm16" and SETTINGS.stream_per_sentence:
        try:
            await asyncio.to_thread(REGISTRY.ensure_loaded, payload.voice_id)
        except EngineUnavailable as exc:
            synthesis_queue.release()
            latency = (time.monotonic() - started) * 1000.0
            METRICS.record(payload.voice_id, "503", latency, error_code=exc.code)
            raise HTTPException(
                status_code=503,
                detail={"code": exc.code, "message": exc.reason},
            ) from exc
        return _streaming_pcm16_response(payload, chunks, started, cache_key, prosody)
    try:
        # Blocking GPU work off the event loop (M2).
        result = await asyncio.to_thread(REGISTRY.synthesize, payload.voice_id, chunks, prosody)
    except EngineUnavailable as exc:
        latency = (time.monotonic() - started) * 1000.0
        METRICS.record(payload.voice_id, "503", latency, error_code=exc.code)
        raise HTTPException(
            status_code=503,
            detail={"code": exc.code, "message": exc.reason},
        ) from exc
    except Exception as exc:  # noqa: BLE001 — m10: never leak a stack trace
        latency = (time.monotonic() - started) * 1000.0
        METRICS.record(payload.voice_id, "503", latency, error_code="synthesis_failed")
        logger.error(
            "synthesis failed",
            extra={
                "fields": {
                    "voice_id": payload.voice_id,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            },
        )
        raise HTTPException(
            status_code=503,
            detail={"code": "synthesis_failed", "message": "Synthesis failed. Try again shortly."},
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
                "preset": prosody.preset,
                "exaggeration": prosody.exaggeration,
                "cfg_weight": prosody.cfg_weight,
                "temperature": prosody.temperature,
            }
        },
    )
    AUDIO_CACHE.put(cache_key, result.pcm16)
    return _audio_response(payload, result.pcm16, latency_ms, cache="miss", prosody=prosody)


def _prosody_headers(prosody: ProsodySettings) -> dict[str, str]:
    """Response headers that say what the preset actually did.

    Honest by construction: exaggeration / CFG are "false" on Turbo
    0.1.7 (verified from the wheel — see api/prosody.py), so a client
    can never mistake a preset for a knob the engine honoured.
    """
    return {
        "X-XploClone-Preset": prosody.preset,
        "X-Prosody-Exaggeration-Effective": str(TURBO_EXAGGERATION_EFFECTIVE).lower(),
        "X-Prosody-CFG-Effective": str(TURBO_CFG_EFFECTIVE).lower(),
    }


def _audio_response(
    payload: TTSRequest,
    pcm16: bytes,
    latency_ms: float,
    cache: str,
    prosody: ProsodySettings,
) -> StreamingResponse:
    """Whole-file response (WAV, or pcm16 when streaming is off)."""
    if payload.format == "pcm16":
        body = pcm16
        media_type = "audio/L16; rate=24000"
    else:
        body = pcm16_to_wav(pcm16, SAMPLE_RATE)
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
            "X-Watermark": "perth-unverified",
            "X-Cache": cache,
            **_prosody_headers(prosody),
            "Content-Disposition": f'attachment; filename="xploclone-{payload.voice_id}.wav"',
        },
    )


def _streaming_pcm16_response(
    payload: TTSRequest,
    chunks: list[str],
    started: float,
    cache_key: str,
    prosody: ProsodySettings,
) -> StreamingResponse:
    """Per-sentence streaming response for pcm16.

    The queue slot is held until the stream finishes (released in the
    generator's finally), so a second request still waits its turn.
    The first chunk is sent after the first sentence is synthesised,
    not after the last one — that is the D4 fix. Total latency is
    recorded when the stream completes.
    """
    collected: list[bytes] = []

    async def _generate() -> AsyncIterator[bytes]:
        try:
            for chunk in chunks:
                try:
                    pcm = await asyncio.to_thread(
                        REGISTRY.synthesize_one, payload.voice_id, chunk, prosody
                    )
                except EngineUnavailable as exc:
                    # Engine died mid-stream: log server-side; the client
                    # sees a truncated stream, which is why callers
                    # should treat a short body as a failure, not audio.
                    logger.error(
                        "streaming synthesis failed",
                        extra={"fields": {"voice_id": payload.voice_id, "error": exc.reason}},
                    )
                    return
                except Exception as exc:  # noqa: BLE001 — same m10 rule
                    logger.error(
                        "streaming synthesis failed",
                        extra={
                            "fields": {
                                "voice_id": payload.voice_id,
                                "error": f"{type(exc).__name__}: {exc}",
                            }
                        },
                    )
                    return
                collected.append(pcm)
                yield pcm
        finally:
            synthesis_queue.release()
            if collected:
                AUDIO_CACHE.put(cache_key, b"".join(collected))
            latency_ms = (time.monotonic() - started) * 1000.0
            METRICS.record(payload.voice_id, "200", latency_ms, chars=len(payload.text))

    return StreamingResponse(
        _generate(),
        media_type="audio/L16; rate=24000",
        headers={
            "X-XploClone-Voice": payload.voice_id,
            "X-XploClone-Chars": str(len(payload.text)),
            "X-Watermark": "perth-unverified",
            "X-Cache": "miss",
            "X-Streaming": "per-sentence",
            **_prosody_headers(prosody),
            "Content-Disposition": f'attachment; filename="xploclone-{payload.voice_id}.pcm16"',
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):  # type: ignore[no-untyped-def]
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
