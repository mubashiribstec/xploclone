# XploClone

Single-owner, self-hosted voice-cloning TTS — **Mubashir Ali's voice only**,
in three variants at most: English (US accent), English (British accent),
and Urdu. It exists to remove the per-minute ElevenLabs bill from his own
products (Xplogent, xplosole) and to give him a voice no vendor can change,
reprice, or take away.

Implements **PLAN-v2** (`PLAN-v2.md`, which supersedes `PLAN-v1.md` after
`AUDIT-v1.md`). Phase 0 + Phase 1 (English MVP) are in this branch.
Urdu is a gated research spike — it is **not** shipped in v1.

## What is built (Phase 0 + Phase 1)

- FastAPI service (`api/`) — `GET /health`, `GET /metrics`,
  `GET /v1/voices`, `POST /v1/tts` (24 kHz WAV / PCM16, streaming).
  Chatterbox Turbo 350M (MIT) for English, lazy-loaded so the API starts
  and tests without a GPU. PerTh watermark preserved on every output.
- Next.js 16.4.3 web UI (`web/`) — Generate page only in Phase 1.
  The browser never talks to the GPU server; the API key never ships to
  the browser (server-side proxy route).
- Recording scripts (`docs/recording-scripts/`), consent template
  (`docs/CONSENT.md`), cost sheet (`docs/COST-SHEET.md`), benchmark
  template (`docs/BENCHMARK.md`), Urdu spike template (`docs/URDU-SPIKE.md`).
- CPU-only CI: lint, type-check, unit tests, Docker build check.

## What is NOT built yet (with gates)

| Item | Phase | Gate / blocker |
|---|---|---|
| Urdu engine (`mubashir-ur`) | 2, gated | `docs/URDU-SPIKE.md` must PASS first. Until then `POST /v1/tts` for `mubashir-ur` returns **503 `engine_unavailable`** — never a silent fallback. |
| Live-call WebSocket `/v1/tts/stream`, 8 kHz μ-law, barge-in | 3 | Gate 3: real phone line with Xplogent, end-to-end turn p95 < 800 ms, GPU-down fallback tested. |
| LoRA fine-tune per voice | 4 | Only if zero-shot fails Gate 1; must beat zero-shot by ≥ 0.5 MOS or revert. |
| Backup/restore (tested), hardening, handover audit | 5 | Audit of the built project; all critical issues fixed or recorded. |
| MP3 output | — | Not in v1. WAV / PCM16 only. Add behind a flag + test if needed. |
| GPU inference | 1 | **Not tested in this environment (no GPU here).** Needs owner/GPU verification — see `docs/BUILD-LOG.md`. Latency figures in PLAN-v2 are targets, not measurements. |

## Quick start (dev, CPU — API logic only, no voice)

```bash
cp .env.example .env          # dev-only placeholder key; change it
uv sync --python 3.14         # creates .venv, installs pinned deps
uv run uvicorn api.main:app --reload --port 8000
curl localhost:8000/health
```

Without reference recordings the English voices report `unavailable` and
`/v1/tts` returns 503. That is correct behaviour, not a bug: no recording,
no voice. Place clips in `api/reference/` (gitignored, never commit them):
`mubashir-en-us.wav`, `mubashir-en-gb.wav` (48 kHz, 16-bit, mono WAV).

## Production (GPU)

```bash
docker compose up --build    # api (CUDA 13.0 / cu130 — see docs/BUILD-LOG.md) + web
```

Requirements: NVIDIA GPU with ≥ 12 GB VRAM, dedicated to TTS (PLAN-v2 D11:
the owner's Z640 / GTX 1660 Super 6 GB is **dev-only**). See
`docs/COST-SHEET.md` for cloud GPU prices and the break-even maths.

## API in brief

```bash
# List voices (public)
curl localhost:8000/v1/voices

# Synthesise (Bearer key required)
curl -X POST localhost:8000/v1/tts \
  -H "Authorization: Bearer $XPLOCLONE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"voice_id":"mubashir-en-gb","text":"Hello, thank you for calling.","format":"wav"}' \
  --output out.wav
```

Limits: max 5,000 chars/request, 60 req/min per key, 1 concurrent
synthesis (FIFO queue max 10, 30 s timeout → 503 `engine_busy`).

## Repo layout

```
api/            FastAPI app (config, voices, auth, rate limit, normalise,
                chunking, engine adapter, audio, metrics, logging)
web/            Next.js 16.4.3 admin UI (Generate page in Phase 1)
tests/          Unit tests (no GPU)
scripts/
  benchmark/    Blind-test harness (manifest, randomisation, WER scoring)
  record/       Recording manifest template
docs/
  COST-SHEET.md  BENCHMARK.md  URDU-SPIKE.md  CONSENT.md  BUILD-LOG.md
  recording-scripts/  en-us.md  en-gb.md  ur.md
Dockerfile.api  Dockerfile.web  docker-compose.yml
pyproject.toml  uv.lock
PLAN-v1.md  PLAN-v2.md  AUDIT-v1.md   (plan history — v2 is authoritative)
```

## Safety rules (non-negotiable)

- Only Mubashir's voice. No voice-upload endpoint, no other voices.
- Recordings / embeddings are sensitive personal data: encrypted at rest,
  never in this (public) repo, never in logs. Outputs deleted after 7 days
  unless explicitly kept.
- PerTh watermark is preserved on every Chatterbox output. Never strip it.
- Synthetic audio must be marked/disclosed per EU AI Act Art. 50
  (in force 2 Aug 2026; new systems have no grace period). Xplogent calls
  keep the AI + recording disclosure in the greeting.
- No secrets in git or chat. API keys live in `.env` / host secret store.
