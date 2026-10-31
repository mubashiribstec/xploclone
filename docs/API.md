# API Reference — XploClone (v0.1.0, Phase 1)

Base URL (local): `http://127.0.0.1:8000`. The browser never calls
this directly — the Next.js web UI proxies through its own
`/api/*` routes server-side. Direct browser calls are not supported
(no CORS middleware; `TrustedHostMiddleware` allows only
localhost / 127.0.0.1 / api / web by default).

Auth: `POST /v1/tts` needs `Authorization: Bearer <API key>`.
The server stores only the SHA-256 hash (`XPLOCLONE_API_KEY_HASH`).
Wrong / missing key → 401. No key hash configured and dev mode off →
503 `auth_not_configured`.

Limits: max 5,000 chars/request, 60 req/min per key, 1 concurrent
synthesis (FIFO queue max 10, 30 s timeout → 503 `engine_busy`).

## GET /health — public

Liveness + readiness. Always answers `status: ok` even during a
synthesis; `ready` is true only when an English voice is loaded.

```bash
curl localhost:8000/health
```
```json
{
  "status": "ok", "ready": false, "version": "0.1.0",
  "engines": {"en": "unavailable", "ur": "unavailable"},
  "voices": {"mubashir-en-us": "unavailable", "mubashir-en-gb": "unavailable", "mubashir-ur": "unavailable"},
  "device": "cuda", "engine": "turbo",
  "chatterbox_revision": "749d1c1a46eb10492095d68fbcf55691ccf137cd",
  "chatterbox_revision_resolved": null
}
```
`engine` is `turbo` or `nano`; `chatterbox_revision_resolved` is the
commit actually loaded (null until loaded; for Nano it may be an
unpinned commit — pin it before Gate 1).

## GET /metrics — public

Prometheus text: `xploclone_requests_total{voice_id,status}`,
`xploclone_chars_total`, `xploclone_latency_ms_p50/p95`,
`xploclone_errors_total{voice_id,code}`,
`xploclone_audio_cache_hits/misses`, `uptime_seconds`.
Counters reset on restart (Phase 5). No secrets, no text, no audio.

```bash
curl localhost:8000/metrics
```

## GET /v1/voices — public

Returns exactly the 3 hardcoded voices, with `loaded` / `unavailable`
per voice. There is no create/delete/upload endpoint.

```bash
curl localhost:8000/v1/voices
```
```json
{"voices": [{"voice_id": "mubashir-en-gb", "language": "en-GB", "accent": "GB",
"engine": "chatterbox-turbo", "status": "unavailable",
"description": "Mubashir Ali, English, British accent."}]}
```

## POST /v1/tts — Bearer key required

```bash
curl -X POST localhost:8000/v1/tts \
  -H "Authorization: Bearer $XPLOCLONE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"voice_id":"mubashir-en-gb","text":"Hello, thank you for calling.","format":"wav"}' \
  --output out.wav
```

Request JSON:

| Field | Type | Notes |
|---|---|---|
| `voice_id` | string, required | `mubashir-en-us` \| `mubashir-en-gb` \| `mubashir-ur` |
| `text` | string, required | 1–5,000 chars (after normalisation, empty → 400) |
| `format` | string, default `wav` | `wav` \| `pcm16` (mp3 → 400 `unsupported_format`) |
| `preset` | string, default `default` | `default` \| `natural` \| `warm` \| `firm` — human-voice style (see below) |
| `style` | string, optional | Alias for `preset` (either may be sent, not two different values) |
| `exaggeration` | number 0.0–1.0, optional | Overrides the preset. Accepted + logged, but **Turbo ignores it** (see below) |
| `cfg_weight` | number 0.0–1.0, optional | Overrides the preset. Accepted + logged, but **Turbo ignores it** (see below) |
| `temperature` | number 0.1–1.5, optional | Overrides the preset (this one Turbo honours) |
| `top_p` | number 0.05–1.0, optional | Overrides the preset (Turbo honours it) |
| `repetition_penalty` | number 1.0–2.0, optional | Overrides the preset (Turbo honours it) |

Out-of-range knobs are Pydantic 422s; an unknown preset is 400
`invalid_preset`. Explicit knobs override the preset; the preset
supplies the rest.

### Prosody presets — what they actually do (read this first)

| Preset | exaggeration | CFG | temperature | top_p | rep. penalty |
|---|---|---|---|---|---|
| `default` | 0.5 | 0.5 | 0.8 | 0.95 | 1.2 |
| `natural` *(recommended)* | 0.7 | 0.3 | 0.9 | 0.95 | 1.2 |
| `warm` | 0.6 | 0.4 | 0.85 | 0.95 | 1.2 |
| `firm` | 0.4 | 0.6 | 0.75 | 0.90 | 1.3 |

**Verified limitation (chatterbox source, 2026-10-30/31):**
`ChatterboxTurboTTS.generate()` accepts `exaggeration` and
`cfg_weight` but IGNORES them — it warns so itself, Turbo sets
`emotion_adv = False` (the exaggeration tensor is dead), and
`inference_turbo` hardcodes `cfg_weight=0.0`. The full ChatterboxTTS
(500M) honours both; it is a Phase 2 candidate, not in this build.
So on Turbo the presets' audible effect comes from
`temperature` / `top_p` / `repetition_penalty` (more sampling
variation = less flat, metronomic delivery). The API still accepts
and logs `exaggeration` / `cfg_weight` and passes them to
`generate()` (future-proof if the engine changes), and every
response says so honestly in its headers — never claim a preset
changed exaggeration or CFG on Turbo.

Tuning procedure: start from `natural`; listen to the SAME script;
change ONE knob at a time (e.g. temperature 0.9 → 1.0 if still flat,
0.9 → 0.85 if unstable); re-listen. Never change two knobs at once.

### Tag policy (vocalisation tags)

File generation (`POST /v1/tts`) only. Whitelisted tags are kept:
`[laugh]`, `[sigh]`, `[chuckle]`, `[gasp]`, `[cough]`. Every other
`[tag]` is stripped before synthesis — `[scream]` or an invented
tag never reaches the model. The live-call path (Phase 3) strips
ALL tags, whitelisted or not.

### Text pipeline (order matters)

1. Tag policy (raw text) → 2. normalisation (numbers, dates,
postcodes) → 3. `humanize_text`: line breaks become sentence breaks,
long sentences (> 180 chars) split at a comma into two short
sentences — one idea per sentence. Punctuation pauses are preserved
as different pauses (comma < full stop < em-dash < line break),
never flattened to commas. No fake breath sounds, no added words.

Response: `200` with `audio/wav` (24 kHz, 16-bit, mono) or
`audio/L16; rate=24000` for pcm16. Headers:
`X-XploClone-Voice`, `X-XploClone-Chars`, `X-XploClone-Latency-Ms`
(whole-file responses only), `X-Watermark: perth-unverified`
(until the GPU watermark-survival test passes),
`X-Cache: hit|miss`, `X-XploClone-Preset`, and the honest effective
flags `X-Prosody-Exaggeration-Effective: false` /
`X-Prosody-CFG-Effective: false` (Turbo), and for pcm16
streaming `X-Streaming: per-sentence`.

The audio cache key includes the prosody (preset + knobs): the same
text in `natural` vs `firm` is different audio and never shares a
cache entry.

Per-sentence streaming (pcm16 only, on by default via
`XPLOCLONE_STREAM_PER_SENTENCE=1`): the first chunk is sent after
the first sentence is synthesised, not after the last one. WAV is
always whole-file (its header needs the total size up front).
Set `XPLOCLONE_STREAM_PER_SENTENCE=0` to disable streaming.

Identical requests are cached in memory (TTL 3600 s, max 32 entries,
configurable via `XPLOCLONE_AUDIO_CACHE_TTL_S` /
`XPLOCLONE_AUDIO_CACHE_MAX_ENTRIES`; 0 disables). A cache hit skips
synthesis entirely and returns `X-Cache: hit`.

### Errors (all JSON: `{"detail": {"code": ..., "message": ...}}`)

| Status | Code | Meaning |
|---|---|---|
| 400 | `unknown_voice` | voice_id is not one of the 3 |
| 400 | `text_too_long` | text > 5,000 chars |
| 400 | `empty_text` | text empty after normalisation |
| 400 | `unsupported_format` | format is not wav/pcm16 |
| 400 | `invalid_preset` | unknown preset, preset/style conflict, or out-of-range knob (bypassing Pydantic) |
| 422 | — | out-of-range prosody knob (`exaggeration`/`cfg_weight` 0–1, `temperature` 0.1–1.5, `top_p` 0.05–1, `repetition_penalty` 1–2) |
| 401 | — | missing / invalid API key |
| 429 | `rate_limited` | 60 req/min per key (Retry-After header) |
| 503 | `engine_unavailable` | Urdu (no engine yet), or English engine/reference missing |
| 503 | `engine_busy` | queue full / timed out (Retry-After: 5) |
| 503 | `auth_not_configured` | no key hash set and dev mode off |
| 503 | `synthesis_failed` | unexpected synthesis error (generic message only) |

A truncated pcm16 stream (stream ends early) must be treated as a
failure, not as audio — retry the request.

## Web UI proxy routes (Next.js, login-gated)

`POST /api/auth/login`, `POST /api/auth/logout`,
`GET /api/voices`, `POST /api/tts` — same contract as the API, but
through a server-side session (60 req/min per session). Unauthenticated
→ 401 JSON for `/api/*`, 307 to `/login` for pages. See
`docs/USER-GUIDE.md`.
