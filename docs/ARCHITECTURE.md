# Architecture — XploClone (Phase 1)

```
Browser ──► Next.js web UI (:3000, login-gated)
                │  server-side proxy only (API key never in browser)
                ▼
           FastAPI (:8000) ──► EngineRegistry ──► Chatterbox Turbo (GPU, 350M)
                │                                   or Nano (CPU, 110M)
                │                              reference clip per voice
                ▼                                   (api/reference/*.wav)
           /health, /metrics, /v1/voices, POST /v1/tts
```

## Components

**API (`api/`, FastAPI 0.162.0, Python 3.14.10).**
`main.py` — endpoints, request logging (metadata only, never text /
audio / keys), TrustedHostMiddleware (same-origin via the proxy only,
no CORS). `config.py` — all settings from the environment, read once
(`XPLOCLONE_DEVICE`, `XPLOCLONE_ENGINE=turbo|nano`,
`XPLOCLONE_TORCH_THREADS`, cache + streaming flags).
`auth.py` — SHA-256 hashed API key, `hmac.compare_digest`, Bearer.
`rate_limit.py` — 60 req/min per key (sliding window) + coarse 120/min
per IP before auth; `SynthesisQueue` — 1 concurrent synthesis, FIFO
max 10, 30 s timeout → 503 `engine_busy`.
`normalize.py` — text normalisation (currency, dates, times, postcodes,
"St." handling). `chunking.py` — sentence splitting, long sentences
split at clause/word boundaries, never silently truncated.
`engine.py` — `EngineRegistry`: lazy Chatterbox load (API starts and
tests without GPU/torch), revision enforcement via
`snapshot_download(repo_id, revision)` + `from_local`, Nano via the
same class with `nano=True` (repo `ResembleAI/chatterbox-nano`),
torch-thread control on CPU, per-chunk `synthesize_one()` and
`synthesize_stream()` generator. Reference clips are re-encoded by
`generate()` on every chunk (the 0.1.7 API exposes no embedding
object) — the registry only caches reference file stats, not
embeddings. `audio.py` — WAV/PCM16 helpers, clipping-safe float→PCM16.
`cache.py` — identical-request audio cache (TTL 3600 s, max 32 entries,
in-memory, per process). `metrics.py` — in-memory counters, Prometheus
text at `/metrics`, latency p50/p95 with linear interpolation,
cache hit/miss counters. Counters reset on restart.

**Web UI (`web/`, Next.js 16.4.3, Node 26.12.1, Tailwind v4).**
Single-owner admin UI behind a login (`web/lib/web-auth.ts`:
SHA-256 password hash + HMAC session cookie, httpOnly, 12 h;
`web/proxy.ts` gates every page/route except `/login` and
`/api/auth/*`). Pages: Generate (`/`), Voices, API keys, Health,
Login. The browser never calls the API directly; `/api/tts` and
`/api/voices` proxy server-side with the server key, rate-limited
per web session (60/min). History (last 50) lives in localStorage.

**Engines.** Turbo (GPU prod, 350M, MIT, 5 s clone, PerTh watermark
inside `generate()`). Nano (CPU test mode, 110M*, MIT, 10 s clone,
vendor claim 3× real-time on 8 CPU cores — unmeasured here).
Urdu: no engine — `mubashir-ur` always returns 503
`engine_unavailable`, never a silent fallback. Full comparison:
`docs/OPEN-SOURCE-CLONERS-2026.md`.

\* Nano "110M" is Resemble's figure; an independent survey reconciled
~217M for the T3 backbone.

## Request flow (POST /v1/tts)

1. Per-IP rate limit (before auth) → 400 validation (voice, length,
   format) → API-key auth → per-key rate limit.
2. Normalise text → chunk into sentences.
3. Audio-cache lookup (voice_id, normalised text, format). Hit →
   return immediately (`X-Cache: hit`), no synthesis.
4. Acquire the synthesis queue slot (1 concurrent).
5. pcm16 + streaming on: validate the engine first (503 before
   headers), then stream chunk-by-chunk via `to_thread` per chunk,
   holding the queue slot until the stream finishes; cache the
   concatenated audio at the end. WAV (or streaming off): synthesise
   all chunks via `to_thread`, cache, return whole file.
6. Errors are generic to the client (no stack traces, no internal
   paths); details go to server logs only.

## Data / storage

No database in v1. Recordings live in `api/reference/` (host,
gitignored, private encrypted store, mounted read-only in Docker).
Model weights download once from Hugging Face into the HF cache
(`HF_HOME=/app/.cache/huggingface`) at the pinned revision. Outputs
are streamed, not stored. Logs are JSON to stdout. No audio in logs.

## Deployment

GPU: `docker-compose.yml` (api CUDA 13.0 image + web), GPU
reservation `driver: nvidia, count: 1`, both services bound to
`127.0.0.1` (localhost/VPN only). CPU: `docker-compose.cpu.yml`
override (CPU image, no GPU reservation, `XPLOCLONE_DEVICE=cpu`,
`XPLOCLONE_ENGINE=nano`). One-click: `./install.sh`. CI: CPU-only
(GitHub Actions, owner-side file — see README). Single GPU = single
point of failure: Xplogent must fall back to Cartesia / ElevenLabs
if TTS is down.

## What is NOT in this architecture (Phases 2–5)

Urdu engine, live-call WebSocket `/v1/tts/stream` (8 kHz μ-law,
barge-in), LoRA fine-tuning, backup/restore, persistent metrics,
multi-user accounts. See PLAN-v2 §11.

## Phase 3 — live-call design (not built yet)

WebSocket session per conversation, per-sentence streaming from the
Phase 1 HTTP path, μ-law 8 kHz output at the edge (synthesise at
native 24 kHz, convert at the edge), barge-in handling, GPU-down
fallback. Gate 3 runs on a real phone line, not on laptop speakers.

**Telephony band (D6).** On a G.711 call, identity must survive in
300 Hz–3.4 kHz — test SIM and listener identity *through* μ-law, not
just on 24 kHz WAV.

G.711 keeps 300–3,400 Hz only. Below 300 Hz (the F0 fundamental for
deep male voices, chest resonance) and above 3,400 Hz (F3/F4, the /s/
vs /f/ distinction) are removed by the channel, not by sampling.
Upsampling cannot restore them; a model can only hallucinate
plausible highs. A clone trained on full-band audio therefore loses
its high-band identity cues on a call, while a telephone-band-trained
clone has nothing to lose. The owner's voice is male, with F0 near
the 300 Hz floor — the band edge is where his identity lives, so the
μ-law test is a gate, not a formality. SIM and listener identity are
measured on audio that has been through μ-law (and, at Gate 3,
through a real phone line); a 24 kHz WAV score does not stand in
for it.

**Watermark through μ-law: UNVERIFIED.** PerTh watermark survival
through μ-law is UNVERIFIED — do not claim it works. The build
reports `perth-unverified` until the generate → transcode to 8 kHz
μ-law → check PerTh detectable test passes on real GPU output
(PLAN-v2 §9.1; gap B3). The μ-law transcode path itself does not
exist yet (gap A5) — it is a Phase 3 prerequisite for this test.
