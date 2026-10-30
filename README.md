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
- Next.js 16.4.3 web UI (`web/`) — single-owner admin UI behind a login
  (see below): Generate, Voices, API keys, and Health pages. The browser
  never talks to the GPU server; the API key never ships to the browser
  (server-side proxy route, per-session rate limit).
- Recording scripts (`docs/recording-scripts/`), consent template
  (`docs/CONSENT.md`), cost sheet (`docs/COST-SHEET.md`), benchmark
  template (`docs/BENCHMARK.md`), Urdu spike template (`docs/URDU-SPIKE.md`).
- CPU-only CI: lint, format check, type-check, unit tests, secret scan,
  Docker build check. **The CI file is committed owner-side after merge**
  (the GitHub App lacks the `workflows` permission) — see
  `.github/workflows/ci.yml` header. No CI has run on GitHub yet.
- MIT `LICENSE` + third-party `NOTICE.md` at the repo root.

## Human-voice checklist (does it sound like him, not like AI?)

- [ ] **Reference quality:** recorded with natural range (neutral,
  warm, firm, questioning — `docs/recording-scripts/` §G), not a
  monotone clean read. 60-second proxy clip unblocks testing;
  20-minute set needed for Gate 1. His clone trains only on his
  own recordings.
- [ ] **Preset:** start from `natural` (exaggeration 0.7 / CFG 0.3).
  Change one knob at a time, re-listen to the SAME script.
  (Turbo 0.1.7 ignores exaggeration/CFG — presets work through
  sampling variation; see `docs/API.md`.)
- [ ] **Blind listen:** owner + ≥ 2 native listeners, randomised
  order, same script across presets and vs ElevenLabs v4 Turbo.
- [ ] **Long-form test:** 2+ minute continuous sample, SIM at start
  vs end (`scripts/benchmark/similarity.py --long-form`, |drift| ≤ 0.05).
- [ ] **SIM (ECAPA-TDNN) ≥ 0.80** vs the clean original reference —
  a speaker check, not a quality check. WER is a floor only and
  must never rank models.

## What is NOT built yet (with gates)

| Item | Phase | Gate / blocker |
|---|---|---|
| Urdu engine (`mubashir-ur`) | 2, gated | `docs/URDU-SPIKE.md` must PASS first. Until then `POST /v1/tts` for `mubashir-ur` returns **503 `engine_unavailable`** — never a silent fallback. |
| Live-call WebSocket `/v1/tts/stream`, 8 kHz μ-law, barge-in | 3 | Gate 3: real phone line with Xplogent, end-to-end turn p95 < 800 ms, GPU-down fallback tested. |
| LoRA fine-tune per voice | 4 | Only if zero-shot fails Gate 1; must beat zero-shot by ≥ 0.5 MOS or revert. |
| Backup/restore (tested), hardening, handover audit | 5 | Audit of the built project; all critical issues fixed or recorded. |
| MP3 output | — | Not in v1. WAV / PCM16 only. Add behind a flag + test if needed. |
| GPU inference | 1 | **Not tested in this environment (no GPU here).** Needs owner/GPU verification — see `docs/BUILD-LOG.md`. Latency figures in PLAN-v2 are targets, not measurements. |

## Quick start — one click

```bash
./install.sh            # auto: GPU if nvidia-smi works, else CPU
./install.sh --gpu      # GPU mode (Turbo, CUDA 13.0)
./install.sh --cpu      # CPU mode (Nano, file generation only)
./install.sh --check-only   # preflight only, changes nothing
```

Then open **http://localhost:3000/login**. The installer prints the
web password **once** — save it. Full instructions:
`docs/INSTALL.md`. Windows: `.\install.ps1` (untested on Windows —
see `docs/INSTALL.md`). Preflight without installing:
`python3 scripts/doctor.py`.

Without reference recordings the English voices report `unavailable` and
`/v1/tts` returns 503. That is correct behaviour, not a bug: no recording,
no voice. Place clips in `api/reference/` (gitignored, never commit them):
`mubashir-en-us.wav`, `mubashir-en-gb.wav` (48 kHz, 16-bit, mono WAV).
Then `docker compose restart api`.

## CPU test mode (no GPU)

```bash
./install.sh --cpu
# or: docker compose -f docker-compose.yml -f docker-compose.cpu.yml up --build -d
python3 scripts/cpu_smoke.py   # API-logic smoke test, no model, no real voice
```

CPU mode uses **Chatterbox Nano** (110M, MIT, `XPLOCLONE_ENGINE=nano`,
`XPLOCLONE_DEVICE=cpu`) — vendor claim 3× real-time on 8 CPU cores,
**unmeasured here**; on a 2-core VM expect slower than real-time.
File generation only, never live calls. Turbo on CPU is a fallback,
not a mode. See `docs/PC-REQUIREMENTS.md` (Tier A) and
`docs/OPEN-SOURCE-CLONERS-2026.md` (§2, incl. the honest ONNX Q4
answer: no official ONNX Q4 Nano release was found).

## Documentation

| Doc | What it covers |
|---|---|
| `docs/INSTALL.md` | One-click, manual, CPU, GPU install; recordings; updates |
| `docs/USER-GUIDE.md` | Web UI: login, Generate, Voices, API keys, Health |
| `docs/API.md` | All endpoints, auth, limits, errors, curl examples |
| `docs/ARCHITECTURE.md` | Components, request flow, data, deployment |
| `docs/TROUBLESHOOTING.md` | Docker, GPU, voices, auth, 401/429/503, CI |
| `docs/PC-REQUIREMENTS.md` | 3 tiers (CPU test / dev GPU / production) + checklist + `scripts/doctor.py` |
| `docs/OPEN-SOURCE-CLONERS-2026.md` | 14 open cloners compared (licence, VRAM, CPU, sample, verdict) |
| `docs/COST-SHEET.md` | Cloud GPU prices + break-even vs ElevenLabs |
| `docs/BENCHMARK.md` | Blind-test template (not run yet) |
| `docs/URDU-SPIKE.md` | Gated Urdu research spike (template, not started) |
| `docs/CONSENT.md` | Voice consent template |
| `docs/BUILD-LOG.md` | Build + fix log, pinned versions, deviations |

## Dev (no Docker — API logic only, no voice)

```bash
cp .env.example .env          # then generate real keys — see .env.example header
#   API key:  python -c "import secrets; print(secrets.token_hex(32))"
#   Key hash: python -c "import hashlib; print(hashlib.sha256(b'YOUR_KEY').hexdigest())"
uv sync --python 3.14         # creates .venv, installs pinned deps
uv run uvicorn api.main:app --reload --port 8000
curl localhost:8000/health
```

## Web UI login

The web UI is a single-owner admin UI. It requires a login: set
`XPLOCLONE_WEB_PASSWORD_HASH` (SHA-256 of the owner password) and
`XPLOCLONE_WEB_SESSION_SECRET` (random secret) in `.env`, then open
`http://localhost:3000/login`. There is no signup and no default
password — with those variables empty, logins are refused. The proxy
routes are also rate-limited per web session (60 req/min).

## Production (GPU)

```bash
docker compose up --build    # api (CUDA 13.0 / cu130 — see docs/BUILD-LOG.md) + web
```

Both services bind to `127.0.0.1` on the host by default — localhost /
VPN only. Do NOT expose `web:3000` publicly as-is; put it behind a
reverse proxy with TLS (or a VPN) first. The API is same-origin via the
Next.js proxy only; direct browser calls are not supported and no CORS
middleware is enabled.

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
                chunking, engine adapter, audio, metrics, logging, cache)
web/            Next.js 16.4.3 admin UI (Generate, Voices, API keys, Health;
                login-gated, see web/lib/web-auth.ts)
tests/          Unit tests (no GPU)
scripts/
  benchmark/    Blind-test harness (manifest, randomisation, WER scoring)
  record/       Recording manifest template
  doctor.py     Preflight: CPU/RAM/disk/GPU/Docker/.env/clips
  cpu_smoke.py  CPU smoke test (synthetic clip, no model, no real voice)
docs/
  INSTALL.md  USER-GUIDE.md  API.md  ARCHITECTURE.md  TROUBLESHOOTING.md
  PC-REQUIREMENTS.md  OPEN-SOURCE-CLONERS-2026.md
  COST-SHEET.md  BENCHMARK.md  URDU-SPIKE.md  CONSENT.md  BUILD-LOG.md
  recording-scripts/  en-us.md  en-gb.md  ur.md
Dockerfile.api  Dockerfile.cpu  Dockerfile.web
docker-compose.yml  docker-compose.cpu.yml
install.sh  install.ps1  install.bat
pyproject.toml  uv.lock
LICENSE  NOTICE.md
PLAN-v1.md  PLAN-v2.md  AUDIT-v1.md   (plan history — v2 is authoritative)
```

## Safety rules (non-negotiable)

- Only Mubashir's voice. No voice-upload endpoint, no other voices.
- Recordings / embeddings are sensitive personal data: encrypted at rest,
  never in this (public) repo, never in logs. Outputs are streamed, not
  stored, by default — there is no stored output to delete. If a
  `store_output` option is ever added (Phase 5), stored outputs will be
  deleted after 7 days.
- PerTh watermark is preserved on every Chatterbox output. Never strip it.
  The watermark is reported as `perth-unverified` until the watermark-
  survival test passes on a real GPU output (see docs/BUILD-LOG.md).
- Synthetic audio must be marked/disclosed per EU AI Act Art. 50
  (in force 2 Aug 2026; new systems have no grace period). Xplogent calls
  keep the AI + recording disclosure in the greeting.
- No secrets in git or chat. API keys live in `.env` / host secret store.
