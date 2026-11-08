# XploClone — Build log (Phase 0 + Phase 1, branch `muse/xploclone-mvp`)

Date: 2026-10-30. Implementer: Muse (subagent). Plan: PLAN-v2 (authoritative).

## Audit-fix entry (2026-10-30, after AUDIT-BUILD-v1.md — 0 Critical, 7 Major, 18 Minor)

All 7 Majors fixed, all 18 Minors fixed except where noted. Head before fixes:
`70b66db37516f65e64dcd4609d6508f68f9f366b` (PR #1, not merged).

| Issue | Fix |
|---|---|
| M1 web UI unauthenticated | Owner login added: `web/lib/web-auth.ts` (SHA-256 password hash + HMAC session cookie, httpOnly, 12 h), `/login` page, `/api/auth/login` + `/api/auth/logout`, and `web/proxy.ts` (Next.js 16 proxy) gating every page/route except `/login` and `/api/auth/*`. The proxy routes also require a session + per-session rate limit (60/min, `web/lib/web-rate-limit.ts`). Compose binds `127.0.0.1:3000` (localhost/VPN only). Live smoke test: `/` → 307 to `/login` without a cookie, `/api/voices` → 401, wrong password → 401, correct password → 200 + cookie, `/` → 200 with cookie. Note: an earlier `(admin)` route-group layout was replaced by the proxy because the snapshot-push procedure cannot delete files — the old `web/app/page.tsx` would otherwise have remained alongside `(admin)/page.tsx` and conflicted on `/`. The proxy returns 401 JSON for `/api/*` and a 307 redirect for pages. |
| M2 sync synthesis blocks loop | `POST /v1/tts` now runs `REGISTRY.synthesize` via `asyncio.to_thread`. New test `test_health_responsive_during_synthesis`: /health answers in < 0.5 s while a 0.8 s synthesis runs. |
| M3 revision pin not enforced | `EngineRegistry.load_english` now downloads via `snapshot_download(repo_id, revision=…)` and loads with `from_local`; a snapshot whose commit ≠ pinned revision fails loudly. `resolved_revision` is exposed in `/health` and the Health page. `huggingface-hub==1.33.0` added as a direct dependency (lock re-resolved, still 147 packages). Tests assert the revision is passed through and mismatches are rejected. |
| M4 no LICENSE | MIT `LICENSE` (Copyright (c) 2026 Mubashir Ali) + `NOTICE.md` (Chatterbox Turbo MIT, resemble-perth, transformers/diffusers Apache-2.0, etc.) added at the repo root. |
| M5 no CI ran | `.github/workflows/ci.yml` fixed locally (see below) but **still NOT pushed** — the App lacks the `workflows` permission (403, known). It must be committed owner-side from a real git checkout after merge. Do not claim CI is green on GitHub. |
| M6 web UI incomplete | Voices, API-keys (env-managed, values never shown), and Health pages added under `(admin)`; Generate + History already existed. |
| M7 known dev key | Removed `dev-only-key-change-me` + its SHA-256 hash from `.env.example` (all secrets now start empty, with generation commands), removed `COPY .env.example` from `Dockerfile.api`, CI now generates a fresh random key/hash at run time. Grep-verified: no trace of the old key/hash remains in the repo (excluding lockfiles). |
| m1 422 vs 400 | Over-long text is now a 400 `text_too_long` (length checked in the endpoint, not by Pydantic `max_length`). Test updated. |
| m2 ISO dates / "St." | ISO dates → spoken dates ("January five, twenty twenty six"); "Main St." → "Main Street", leading "St. John" → "Saint John". Tests added. |
| m3 postcode digits | Postcodes are expanded after the integer pass, so digits stay digits ("S W 1 A 1 A A"). Test asserts the full string. |
| m4 lowercase sentences | Sentence splitter accepts lowercase starts. Test added. |
| m5 rate-limit key | Limiting is keyed on the token hash (via `bearer_token` + `hash_key`), plus a coarse per-IP limiter (120/min) applied before auth. Lowercase `bearer` test added. |
| m6 max_chars unused | `SETTINGS.max_chars` is now enforced in the endpoint (m1 fix). |
| m7 health warmup | `/health` now reports liveness (`status: ok`) separately from readiness (`ready`), plus `resolved_revision`. Optional startup warmup behind `XPLOCLONE_WARMUP_ON_STARTUP` / `XPLOCLONE_WARMUP_GENERATE` (off by default). |
| m8 watermark claim | Header/result now report `perth-unverified` until the GPU watermark-survival test passes. No unmeasured claim. |
| m9 load errors leak | Load errors are logged server-side; clients get only "Chatterbox Turbo failed to load. Check the server logs." Test asserts no internal text leaks. |
| m10 unhandled 500 | Generic `except Exception` around synthesis → 503 `synthesis_failed` with metrics + log, no stack trace. Test added. |
| m11 PCM clipping | Engine uses `float_samples_to_pcm16` (clips) instead of a raw cast. |
| m12 root in Docker | `appuser` (uid 10001) in `Dockerfile.api`; `node` user in `Dockerfile.web` runner stage. |
| m13 compose .env | `.env` is now optional (`required: false`) for the API; the web service gets only the variables it needs via `environment:`, no `env_file`. |
| m14 dead `next lint` | Removed the dead script; added `npm run typecheck` (`tsc --noEmit`), run in CI. A full ESLint flat config is deferred (recorded here, not silently dropped). |
| m15 CI gaps | CI (local file) now has `ruff format --check`, web `typecheck`, a secret scan for the old dev key, Docker layer caching (`docker/build-push-action`, `cache-from/to: type=gha`), and `npm audit --audit-level=high` for the web. |
| m16 7-day retention claim | README + CONSENT reworded: outputs are streamed, not stored, by default — there is no stored output to delete. |
| m17 CORS / TrustedHost | `TrustedHostMiddleware` added (allowed hosts from `XPLOCLONE_ALLOWED_HOSTS`, default localhost/127.0.0.1/api/web; `testserver` added by tests). Documented: same-origin via Next.js proxy only, no CORS. |
| m18 percentile | `_percentile` now uses linear interpolation. Tests added. |

### Fix re-verification (this environment, 2026-10-30)

Local env: Python **3.14.10** (uv-managed — the pinned interpreter, unlike the
audit's 3.12.3 re-run), Node 24.22.1 (PLAN fallback; Node 26.12.1 is pinned
for Docker/CI). No GPU, no Docker in this VM.

| Check | Result |
|---|---|
| `pytest -q` | ✅ **46 passed, 0 failed** (was 34; +12 new tests for the fixes) |
| `ruff check api tests scripts` | ✅ pass |
| `ruff format --check api tests scripts` | ✅ pass |
| `mypy api` | ✅ pass, no issues in 12 source files |
| `npm ci && npm run typecheck && npm run build` (web) | ✅ pass; routes `/`, `/login`, `/voices`, `/keys`, `/health`, `/api/auth/*`, `/api/tts`, `/api/voices` |
| Web login smoke (live `next start`) | ✅ `/` → 307 `/login` unauthenticated; `/api/voices` → 401; wrong password → 401; correct password → 200 + cookie; `/` → 200 authenticated |
| `uv lock --check` | ✅ 147 packages, `huggingface-hub` now a direct dep (1.33.0) |
| `docker build` | ❌ **NOT RUN — no Docker in this VM.** CI must prove it (owner-side file). |
| GPU inference | ❌ **NOT RUN — no GPU in this VM.** Revision enforcement is proven by wiring tests only; a real GPU load is still required before Gate 1. |

### Still unverified (do not claim otherwise)

- Docker builds (API + web), GPU inference, TTFA/latency, audio quality,
  speaker similarity, accent separation, watermark survival through μ-law,
  ElevenLabs benchmark (Gate 1), Urdu spike (Gate 0), live-call streaming
  (Phase 3), fine-tuning (Phase 4), backup/restore (Phase 5).
- CI on GitHub: the workflow file is not on the branch (M5) — no check
  runs exist for PR #1 until the owner commits it after merge.
- ESLint flat config for the web UI is deferred (m14); `typecheck` runs in CI instead.
- The `appuser` Docker change and the CUDA 13.0 driver requirement are
  unproven until a real Docker build + GPU run.

## Versions pinned (verified at build — method in brackets)

| Component | Pinned | Verified how |
|---|---|---|
| Python | **3.14.10** (`>=3.14,<3.15`, never 3.15) | `uv python install 3.14.10` (uv 0.13.6); tests + lock run on it |
| uv | **0.13.6** | `uv --version` |
| PyTorch | **2.14.1+cu130** (see deviation D1) | `pip index versions torch` on cu130 index |
| torchaudio | **2.11.0+cu130** (see deviation D2) | `pip index versions torchaudio` on cu130 index |
| FastAPI | **0.162.0** | `pip index versions fastapi` (latest) |
| Pydantic | **2.14.2** | `pip index versions pydantic` (latest) |
| Uvicorn | **0.54.0** (`uvicorn[standard]`) | `pip index versions uvicorn` (latest) |
| chatterbox-tts | **0.1.7** (MIT) | `pip index versions chatterbox-tts`; wheel inspected |
| Chatterbox Turbo weights | HF `ResembleAI/chatterbox-turbo`, rev **`749d1c1a46eb10492095d68fbcf55691ccf137cd`** | Hugging Face API, 2026-10-30; MIT, English-only |
| Chatterbox Turbo API | `ChatterboxTurboTTS.from_pretrained(device)`, `generate(text, audio_prompt_path=...)`, PerTh watermark applied inside `generate()`, output 24 kHz (`S3GEN_SR = 24000`) | Read from the 0.1.7 wheel (`chatterbox/tts_turbo.py`) |
| soundfile | **0.14.0** | pip index (latest) |
| numpy | **2.5.4** | pip index (latest) |
| httpx | **0.28.1** | pip index (latest) |
| transformers / diffusers / librosa / gradio / safetensors / resemble-perth | 5.2.0 / 0.29.0 / 0.11.0 / 6.8.0 / 0.5.3 / 1.0.1 | Resolved by `uv lock` from chatterbox-tts 0.1.7 requirements |
| Next.js | **16.4.3** | npm registry (latest 16.4.3, 23 Oct 2026); `npm install --package-lock-only` |
| React / React DOM | **19.3.1** | npm registry (latest) |
| sharp | **0.35.5** | npm registry (latest; ≥ 0.35.5 required post-RCE) |
| Tailwind CSS / @tailwindcss/postcss | **4.3.3** | npm registry (latest v4) |
| TypeScript | **5.9.3** | npm registry (resolved by lockfile) |
| Node (Dockerfile/CI) | **26.12.1** | PLAN-v2 pin; local build used 24.22.1 (fallback, see below) |
| Docker base (API) | **nvidia/cuda:13.0.0-runtime-ubuntu24.04** (see D1) | Docker Hub tags API — tag exists |
| Docker base (web) | **node:26.12.1-bookworm-slim** | PLAN-v2 pin (tag not re-verified; CI build will prove it) |

Full transitive pins: `uv.lock` (147 packages) and `web/package-lock.json`.

## Deviations from PLAN-v2 (plan-vs-reality — read before audit)

### D1 — PyTorch CUDA is cu130, NOT cu128 (material)
PLAN-v2 §3.1 pins "PyTorch 2.14.1, CUDA 12.8 (cu128)". That combination
**does not exist as a published wheel** (verified 2026-10-30):
- `download.pytorch.org/whl/cu128` tops out at torch **2.11.0+cu128**.
- `.../cu129` tops out at torch **2.13.0+cu129**.
- `.../cu130` lists torch **2.14.1+cu130** as latest.

So v1 pins `torch==2.14.1+cu130` and the API image uses
`nvidia/cuda:13.0.0-runtime-ubuntu24.04`. The torch *version* (2.14.1)
and Python (3.14.10) pins are kept; only the CUDA flavour changed.
Consequence: the prod host needs a CUDA 13.0-capable NVIDIA driver
(R570+ family — confirm on the prod host; do not assume the Z640's
driver supports it). If CUDA 13.0 is a problem, the fallback is
torch 2.11.0+cu128 — a downgrade that must be a recorded decision,
not a silent swap.

### D2 — torchaudio has no 2.14 build (minor)
The newest torchaudio anywhere (PyPI and all CUDA indexes checked) is
**2.11.x**; cu130 tops out at `torchaudio==2.11.0+cu130`. It satisfies
chatterbox-tts 0.1.7's `torchaudio>=2.9.0` (Python ≥ 3.14). The
torch/torchaudio minor-version mismatch (2.14 vs 2.11) is a known risk:
chatterbox-tts's Turbo path does not import torchaudio (verified from
the 0.1.7 wheel — `tts_turbo.py` imports librosa/torch/perth only), so
the risk is low, but it must be confirmed by a real GPU generation
before Gate 1.

### D3 — MP3 output is not implemented in v1
PLAN-v2 §6.1 lists `wav | mp3 | pcm16`. v1 implements `wav` and `pcm16`
only; `format=mp3` returns 400 `unsupported_format`. Reason: MP3 needs
ffmpeg at request time and adds a transcoding failure mode the MVP
does not need. Add it behind a flag + test if the owner asks.

### D4 — HTTP streaming is per-request, not per-sentence
`POST /v1/tts` synthesises sentence-by-sentence (engine-level
chunking) but returns the complete WAV in one streaming response.
True per-chunk HTTP streaming (first bytes before the last sentence
finishes) is a Phase 3 refinement for the WebSocket path.

## Test results (this environment, 2026-10-30)

Local env: Python 3.14.10 (uv-managed), Node 24.22.1 (PLAN fallback —
Node 26.12.1 is pinned for Docker/CI; the local web build ran on 24.22.1
because that is what this VM has). No GPU in this environment.
Docker is **not installed** in this VM (`docker: command not found`).

| Check | Result |
|---|---|
| `ruff check api tests scripts` | ✅ pass (7 issues found and fixed during the build) |
| `ruff format` | ✅ applied (6 files reformatted) |
| `mypy api` | ✅ pass, no issues in 12 files (2 errors found and fixed) |
| `pytest -q` | ✅ **34 passed** (1 initial failure: a wrong test expectation for £13.50 — fixed the test, not the code) |
| Live smoke (TestClient, real app) | ✅ `/health` ok; `/v1/voices` lists 3 voices, all `unavailable` (no recordings); Urdu → **503 `engine_unavailable`**; en-gb with no reference → **503 `engine_unavailable`**; wrong key → 401 |
| `uv lock` | ✅ 147 packages resolved |
| `npm ci && npm run build` (web) | ✅ succeeds; routes `/`, `/api/tts`, `/api/voices` |
| `docker build` | ❌ **NOT RUN — no Docker in this VM.** CI must prove it. |

## NOT tested (needs owner / GPU host — do not claim otherwise)

- [ ] GPU inference: Chatterbox Turbo has never been loaded in this
  build. No latency (TTFA p50/p95), no audio quality, no watermark
  check, no VRAM measurement. First GPU run must be on a CUDA 13.0
  host with a 60-second proxy recording per variant.
- [ ] Docker image builds (API + web) — CI only.
- [ ] Real voice similarity / accent separation — needs recordings.
- [ ] ElevenLabs benchmark (docs/BENCHMARK.md is a template).
- [ ] Urdu spike (docs/URDU-SPIKE.md is a template, not started).
- [ ] `torch.compile` on Python 3.14 + torch 2.14.1 (not used in v1).

## Known limitations recorded for the audit

1. D1/D2 above (CUDA flavour + torchaudio mismatch).
2. In-memory rate limiting and metrics reset on restart (Phase 5).
3. Single concurrent synthesis (by design, PLAN-v2 §6.4).
4. No audio is stored by default; no retention job yet (Phase 5).
5. Web UI history lives in the browser (localStorage, last 50).

## Improvement round — one-click install, CPU mode, docs, optimisation (2026-10-30)

Head before this round: `c4ca337b8fd35c3d7e4fbcdafd7a24f54c7312a6` (PR #1, not merged).

### What was added

- **One-click install:** `install.sh` (Linux/macOS; `--help/--cpu/--gpu/--check-only/--dry-run`),
  `install.ps1` + `install.bat` (Windows, **untested** — no Windows host here).
  Checks Docker + Compose, warns (does not fail) if no GPU, creates `.env` (mode 600)
  with fresh random API key/hash, web password hash + session secret (password printed
  once, never stored in plaintext), creates `api/reference/`, runs the right compose
  profile, waits up to 180 s for `/health`. README quick start is now literally
  `./install.sh` then open `http://localhost:3000/login`.
- **CPU mode:** `docker-compose.cpu.yml` (override — no GPU reservation, `Dockerfile.cpu`
  with torch 2.14.1+cpu / torchaudio 2.11.0+cpu, verified to exist for cp314 on the
  CPU index) + `XPLOCLONE_ENGINE=turbo|nano` (default turbo; nano on CPU) +
  `XPLOCLONE_TORCH_THREADS`. Nano = same `ChatterboxTurboTTS` class with `nano=True`
  (HF `ResembleAI/chatterbox-nano`, MIT), verified from the model card 2026-10-30.
  `scripts/cpu_smoke.py` (synthetic sine clip, chunking, cache, TestClient /health +
  /v1/voices in CPU/Nano mode — no model, no real voice) and `scripts/doctor.py`
  (preflight: OS/Python/CPU/RAM/disk/GPU/Docker/.env/clips, `--json`, `--gpu`).
- **PC requirements:** `docs/PC-REQUIREMENTS.md` — Tier A CPU test (4–8 cores, 8–16 GB RAM),
  Tier B dev GPU (Z640 + GTX 1660 Super 6 GB dev-only; RTX 3060 12 GB recommended),
  Tier C production (≥12 GB VRAM dedicated, CUDA 13.0 driver), model/VRAM table, checklist.
- **Docs:** `docs/INSTALL.md`, `docs/API.md` (only endpoints that exist), `docs/ARCHITECTURE.md`,
  `docs/TROUBLESHOOTING.md`, `docs/USER-GUIDE.md`, `docs/OPEN-SOURCE-CLONERS-2026.md`
  (14 models + Nano-size caveat; licences verified from primary sources; ONNX Q4 Chatterbox
  **not found** — no official ONNX Q4 Nano release, MLX 4-bit is Apple Silicon only).
  `.env.example` gained the engine/nano/cache/thread vars. CI gained install
  `--check-only` / doctor / CPU-smoke steps and a CPU image build check
  (local file only — still excluded from push, M5).
- **Optimisations:** per-sentence pcm16 streaming (`synthesize_stream()` generator +
  `X-Streaming: per-sentence`; first byte measured <0.65 s with a 0.4 s/chunk fake,
  2 chunks — test `test_pcm16_streams_first_chunk_early`); identical-request audio
  cache (`api/cache.py`, TTL 3600 s, max 32 entries, `X-Cache: hit|miss`,
  `xploclone_audio_cache_hits/misses` in /metrics); torch-thread config on CPU;
  reference-stat cache in `has_reference()`. **Reference-embedding caching was NOT
  implemented** — the 0.1.7 API takes `audio_prompt_path` per `generate()` call and
  exposes no embedding object to cache; claiming it would be false. WAV stays
  whole-file (header needs total size).

### Before / after (measured in this environment)

| Item | Before | After |
|---|---|---|
| Install | manual `.env`, manual keys, `docker compose up --build` | `./install.sh` (dry-run/--help/--check-only verified on this CPU-only VM; real Docker run NOT tested — no Docker here) |
| CPU mode | none — compose reserves an NVIDIA GPU | `docker-compose.cpu.yml` + Nano wiring; Docker build NOT tested (no Docker here); real Nano synthesis on CPU **unmeasured** |
| Tests | 46 passed | **55 passed, 1 skipped** (new: cache, streaming, CPU config, Nano repo, unknown-engine; 1 gated CPU-smoke test) |
| First byte (pcm16, fake 0.4 s/chunk) | after last sentence (~0.8 s) | <0.65 s (test asserts) |
| GPU latency / TTFA / quality | unmeasured | still **unmeasured** — no GPU here; do not quote numbers |

### Bugs found and fixed during this round (verify, don't trust the summary)

1. **`api/engine.py` was syntactically broken** — an earlier edit had inserted the
   Nano constants and `_set_torch_threads()` *inside* the module docstring, so the
   file did not parse (`SyntaxError` at line 21, `torch's`). The header was rebuilt
   (docstring closed, `REPO_ID_NANO` + `_set_torch_threads()` moved to module level).
   Lesson: the new tests had never actually run before this round — the "expect 46+"
   baseline was from the audit, not from the edited code. Fixed and re-verified:
   `pytest -q` → 55 passed.
2. **`uv sync` fails in this VM** — hatchling is missing from the isolated build env
   (`ModuleNotFoundError: No module named 'hatchling.build_meta'`, reproducible).
   Tests were run with the earlier session's venv `/tmp/xploclone-fix-venv`
   (fastapi 0.162.0, pytest 8.3.4). A fresh broken `.venv` created by that attempt
   was removed. This is a VM/tooling issue, not a repo issue — CI uses pip, not uv.
3. `install.sh --dry-run` used to die on missing Docker before showing anything and
   would have created `.env` before the dry-run exit — reordered: dry-run now exits
   before any file change and shows the exact compose command (exit 0).
4. `scripts/cpu_smoke.py` set `XPLOCLONE_ALLOWED_HOSTS` after `api.config` was already
   imported (→ 400 Invalid host header) and assumed short sentences chunk separately
   (they are joined by design) — both fixed; smoke now passes.
5. One test failed on the frozen `Settings` dataclass (`FrozenInstanceError`) — fixed
   by replacing the object with `dataclasses.replace` instead of mutating it.

### Test results (this environment, 2026-10-30, after fixes)

Local env: 2 CPU cores, 7.7 GB RAM, 151.9 GB disk free, Python 3.12.3 system,
Node 24.22.1, no Docker, no GPU. Tests run with `/tmp/xploclone-fix-venv`
(Python 3.14.10, fastapi 0.162.0, pytest 8.3.4).

| Check | Result |
|---|---|
| `pytest -q` | ✅ **55 passed, 1 skipped** (gated CPU-smoke sine test) |
| `ruff check api scripts tests` | ✅ pass |
| `ruff format --check api scripts tests` | ✅ pass (4 files reformatted in this round) |
| `mypy api` | ✅ pass, no issues in 13 source files |
| `npm ci && npm run typecheck && npm run build` (web) | ✅ pass |
| `./install.sh --help` | ✅ prints usage, exit 0 |
| `./install.sh --check-only` | ✅ fails clearly (Docker missing), exit 1 — correct on this VM |
| `./install.sh --dry-run --cpu/--gpu` | ✅ shows exact compose command, creates no files, exit 0 |
| `python3 scripts/doctor.py` (+ `--json`) | ✅ reports CPU/RAM/disk/GPU/Docker/.env/clips, exit 1 (Docker missing) — correct |
| `python3 scripts/cpu_smoke.py` | ✅ PASS (synthetic clip, chunking, cache, /health + /v1/voices in CPU/Nano mode) |
| `docker build` (api / cpu / web) | ❌ **NOT RUN — no Docker in this VM.** CI must prove it. |
| Real Nano synthesis on CPU | ❌ **NOT RUN — no model download attempted here.** Unmeasured. |
| GPU inference / TTFA / quality | ❌ **NOT RUN — no GPU here.** Unmeasured. |

## Human-voice round — prosody, tags, pauses, SIM/drift (2026-10-30, 21:53 PKT)

Head before this round: `fb049dff5be02233ced5575cc35ea2a9c1915b6a` (PR #1, not merged).
Request: "update the code with new skill — i need real human voice and its not look ai is speaking."
Skill: `~/workspace/custom-skills/voice-cloning/` v1.0.0 (gaps A1 SIM, A2 drift, A3/A4 prosody/tag policy).

### Finding D5 — Turbo 0.1.7 IGNORES exaggeration/CFG (material, verified from the wheel)

`ChatterboxTurboTTS.generate()` accepts `exaggeration` / `cfg_weight`
as arguments but ignores them: it warns "CFG, min_p and exaggeration
are not supported by Turbo version and will be ignored";
`Turbo.from_local` sets `hp.emotion_adv = False`, so the conditioning
encoder has no `emotion_adv` projection (the value passed to
`prepare_conditionals` is dead); `inference_turbo` hardcodes
`cfg_weight=0.0` and never receives one. The full `ChatterboxTTS`
(500M, `tts.py`) DOES honour both (emotion_adv on by default, CFG
duplicates text tokens and passes cfg_weight to `t3.inference`).
Consequence: the API still accepts/logs/passes exaggeration/CFG
(future-proof), but presets get their audible effect from the
sampling knobs Turbo DOES honour (temperature / top_p /
repetition_penalty), and every response header says
`X-Prosody-Exaggeration-Effective: false` /
`X-Prosody-CFG-Effective: false`. Swapping in the full 500M model so
exaggeration/CFG actually work is a Phase 2 candidate, not in this
round. Do NOT claim a preset changed exaggeration or CFG on Turbo.

### What was added

- **Prosody controls (`api/prosody.py`, new):** `POST /v1/tts` fields
  `preset` (`default|natural|warm|firm`), `style` (alias),
  `exaggeration` / `cfg_weight` (0.0–1.0), `temperature` (0.1–1.5),
  `top_p` (0.05–1.0), `repetition_penalty` (1.0–2.0). Presets:
  natural 0.7/0.3 (temp 0.9), warm 0.6/0.4 (0.85), firm 0.4/0.6
  (0.75, top_p 0.90, rep 1.3), default 0.5/0.5 (0.8). Explicit knobs
  override the preset. Unknown preset → 400 `invalid_preset`;
  out-of-range knob → 422. Values are logged (no text).
- **Engine pass-through (`api/engine.py`):** `synthesize` /
  `synthesize_one` / `synthesize_stream` take an optional
  `ProsodySettings`; `_synthesise_one` passes all six knobs to
  `turbo.generate()`. `SynthesisResult` records the requested
  prosody + `exaggeration_effective=False` / `cfg_effective=False`.
- **Tag policy (`api/normalize.py`):** `apply_tag_policy()` —
  file generation keeps `[laugh] [sigh] [chuckle] [gasp] [cough]`
  only; every other `[tag]` is stripped (tag-injection test added);
  `allow_tags=False` strips ALL tags (Phase 3 live-call default).
- **Natural pauses (`api/normalize.py`):** `humanize_text()` —
  line breaks become sentence breaks, sentences > 180 chars split
  at a comma (one idea per sentence), no fake breaths/noise.
  Normalisation no longer flattens pauses: em/en-dash → ` - `,
  ellipsis → `. ` (was `, ` for all three).
- **Cache (`api/cache.py`, `api/main.py`):** cache key now includes
  the prosody fragment — same text in `natural` vs `firm` never
  shares an entry (test added: natural miss → natural hit → firm miss).
- **SIM + drift (`scripts/benchmark/similarity.py`, new):**
  cosine similarity with NAMED embedding ECAPA-TDNN (SpeechBrain
  `spkrec-ecapa-voxceleb`, same model both sides; anything else is
  an error), 16 kHz mono WAV only (wrong rate = error, never a
  silent resample), `--long-form` drift test (first vs last 30 s
  window of a 2+ min sample, |drift| > 0.05 flagged). Missing
  SpeechBrain fails loudly with install instructions — never a
  faked score. `docs/BENCHMARK.md`: SIM row now names ECAPA-TDNN,
  drift row added, WER documented as floor-only (never rank by WER).
- **Recording scripts:** en-us / en-gb gained §G conversational
  range (neutral, warm, firm, questioning — not acted drama), §H
  long-form 2+ minute one-take passage, and the monotone warning
  (a monotone clean read produces a monotone clone). ur.md gained
  §E conversational range + long-form note. Accent minimal sets
  UNCHANGED.
- **Web UI (`web/app/page.tsx`, `web/app/api/tts/route.ts`):**
  preset picker (Natural/Warm/Firm/Default, Natural pre-selected),
  advanced exaggeration/CFG sliders with per-preset defaults and
  the honest note that Turbo ignores those two knobs; proxy
  forwards prosody fields; history records the preset.
- **Docs:** `docs/API.md` (fields, preset table, D5 limitation,
  tag policy, pipeline order, new headers/errors),
  `docs/USER-GUIDE.md` (how to get a human voice), README
  human-voice checklist.

### Test results (this environment, 2026-10-30)

Local env: Python 3.12.3 system; tests run with a fresh venv
`~/workspace/.venvs/xploclone-test` (fastapi 0.162.0, pytest, ruff,
mypy, numpy — the earlier `/tmp/xploclone-fix-venv` was wiped with
`/tmp` on VM replacement). Node 24.22.1. No GPU, no Docker.

| Check | Result |
|---|---|
| `pytest -q` | ✅ **100 passed, 1 skipped** (was 55; +45 new: prosody, tags/humanize, similarity, API preset/cache) |
| `ruff check api tests scripts` | ✅ pass |
| `ruff format --check api tests scripts` | ✅ pass |
| `mypy api` | ✅ pass, no issues in 14 source files |
| `npm run typecheck && npm run build` (web) | ✅ pass |
| GPU inference / latency / MOS / SIM on real audio | ❌ **NOT RUN — no GPU, no recordings here.** Unmeasured. |

### Bugs found and fixed during this round (verify, don't trust the summary)

1. `tests/test_cache.py`'s `counting` wrapper (and the conftest /
   streaming fakes) took 2 args while `main.py` now passes prosody
   positionally — the first run failed 503 via TypeError. All fakes
   updated to accept `prosody=None`.
2. Tag regex did not allow `-` in tag names, so `[evil-laugh]`
   survived stripping — regex now allows `[A-Za-z _-]` and the
   injection test covers it.
3. `api/normalize.py` edit initially left a stray `"""` + a
   `from __future__` import after function definitions (SyntaxError
   risk) and a `\\s` in a raw regex — both fixed, file parses.
4. Ruff `--fix` unquoted `"_FakeTensor"` annotations in
   `tests/test_prosody.py` without postponed evaluation — added
   `from __future__ import annotations` to that file.

### Still unverified (do not claim otherwise)

- Whether any preset actually sounds more human — needs his
  recordings + a blind listener test (Gate 1). No MOS, no SIM on
  real audio, no latency/quality numbers from this round.
- Docker builds, GPU inference, watermark survival through μ-law,
  ElevenLabs benchmark, Urdu spike, live-call streaming (Phase 3).
- CI on GitHub: the workflow file is still not on the branch (M5).

## Professional UI round (2026-10-30)

Audit found 11 issues (U1–U11, see `docs/UI-CHECKLIST.md`): 5-line
globals.css with no design system, nav with no active state, login
with no show/hide, dead History list, no sample/copy/clear/re-generate
controls, stale preset label after slider moves, no API-down retry,
Voices/Health with no refresh or action, Keys with no copy buttons.
All fixed. New: design system in `globals.css` (focus rings,
touch-sized range thumbs, toast/fade), dark sticky nav with active
pill + working Sign out (`components/SiteNav.tsx`), shared
`components/ui.tsx` (CopyButton with clipboard fallback, Badge),
Generate as a two-column workspace (text/result/history + voice/
preset/advanced sidebar), full-text history with Load/Delete/two-step
Clear, 3 sample buttons, temperature/top-p/repetition-penalty sliders
+ Custom badge + Reset-to-preset, new `GET /api/health` web proxy
route (only API change; FastAPI untouched). Verification:
`npm run typecheck` pass, `npm run build` pass (12 routes),
`ruff check` + `ruff format --check` pass, `mypy api` clean,
`pytest -q` 100 passed, 1 skipped. Live smoke test of the built app
(test password hash, port 3100): login 200 / wrong password 401 /
unauthenticated 307 to /login, all pages 200 authenticated, logout
clears the session, `/api/voices` + `/api/health` correctly 502 with
no API running. End-to-end audio generation in the browser still
needs GPU + recordings — not claimed.

## API bugfix round — 503 on every synthesis + no Nano support (2026-10-31)

Found by the sample test (`~/workspace/xploclone-sample-test/TEST-REPORT.md`):
`POST /v1/tts` returned 503 `synthesis_failed` after 32.7 s on CPU/Nano,
and the same bug would hit GPU/Turbo too.

| Bug | Cause (verified from source) | Fix |
|---|---|---|
| B1 dtype crash | chatterbox `norm_loudness()` multiplies the float32 reference by a `numpy.float64` gain (pyloudnorm) → float64 audio → s3tokenizer matmuls float32 mel filters against float64 → `RuntimeError: expected scalar type Double but found Float` | `api/engine.py: fix_norm_loudness_dtype()` wraps the loaded model's `norm_loudness` to cast its output back to float32, preserving loudness normalisation. `_synthesise_one` now passes `norm_loudness=True` explicitly (the earlier test workaround `norm_loudness=False` is NOT used in production). Regression tests in `tests/test_engine.py` (float64-in → float32-out; generate called with `norm_loudness=True`). |
| B2 no Nano support in the pin | PyPI `chatterbox-tts==0.1.7` has no Nano support: `from_local` hardcodes `t3_turbo_v1.safetensors`, Nano ships `t3_nano_v1.safetensors`; `_load_turbo(nano=True)` → TypeError → FileNotFoundError | Code pinned to git master commit `5de7a54aa4e5e2baadb0182dde554908b48b85c2` (verified in the sample-test venv: Nano loads via `from_local(nano=True)`, Turbo path intact). `pyproject.toml` now uses `chatterbox-tts @ git+https://github.com/resemble-ai/chatterbox.git@5de7a54…`, `uv.lock` re-resolved (147 packages; only change besides the chatterbox source is transitive `resemble-perth` 1.0.1 → 1.1.0 from git master — the same version already in the tested scratch venv). `Dockerfile.cpu` installs the same git pin. Nano weights pinned in `api/config.py` to snapshot `71ccd1d0081b430592cea481f4307e764e07bc64` (the commit downloaded and tested 2026-10-31). Do NOT float the pin or return to 0.1.7 without re-running the Nano + Turbo load tests. |
| B3 NO_PROXY crash | This VM's `NO_PROXY` contains bare IPv6 entries (`fd8b:…::1`); httpx raises `InvalidURL` on them, breaking `snapshot_download` | New `api/proxy_env.py`: `sanitise_no_proxy()` drops bare-IPv6 entries only (bracketed `[::1]` kept). Called from `api/__init__.py` at import and in `_download_checkpoint` before the download. Tests in `tests/test_proxy_env.py`. |

Verification (this VM, no GPU, 2 cores): `pytest -q`, `ruff`, `mypy`,
`npm run build` (see below); API re-test end-to-end on CPU/Nano with
the LibriSpeech sample AND with the owner's own 14.7 s voice note —
`POST /v1/tts` returns 200 with real WAV (timings in the test report
below). Turbo synthesis still NEVER run anywhere — no GPU here.

Verification (this VM, 2026-10-31, after the fixes): `pytest -q`
**105 passed, 1 skipped** (was 100; +5 new: dtype regression x2,
NO_PROXY x3). `ruff check` + `ruff format --check` pass,
`mypy api` clean (15 files), `npm run typecheck` + `npm run build`
pass (12 routes). API re-test end-to-end on CPU/Nano (scratch venv,
git-master chatterbox, cached Nano weights): `POST /v1/tts`
**HTTP 200 both times** — en-gb (LibriSpeech ref) 64.9 s incl. model
load, 5.12 s WAV, 245,804 bytes, 96.8% non-zero; en-us (owner's own
14.7 s note) 27.4 s, 7.04 s WAV, 337,964 bytes, 99.7% non-zero;
`/v1/voices` reports both voices `loaded` afterwards. Server log
clean except the expected Nano "CFG/min_p/exaggeration not supported"
warning (D5). Outputs:
`~/workspace/xploclone-sample-test/phase-a-retest/api-en-gb-librispeech.wav`
and `api-en-us-his-voice.wav` (test outputs only, NOT in the repo).
Turbo synthesis still NEVER run anywhere — no GPU here.

## Urdu spike push (2026-10-31) — head 8ccde290

Pushed `docs/URDU-SPIKE.md` (status NOT STARTED → DONE 2026-10-31,
verdict FAIL) + new `docs/URDU-SPIKE-RESULT.md`. DeepSpeak-v1
(Apache-2.0, checkpoint SHA-256 verified) generates intelligible
Urdu script but SIM 0.06–0.16 vs the owner (target 0.80) — speaker
conditioning not taking effect; Roman Urdu unintelligible. Kani-TTS
Urdu fixed voice, no cloning. Piper `ur_PK` intelligibility baseline
only. Dia-1.6B-Urdu loads on CPU, generation untested — needs a GPU
run. No voice files or audio samples in the commit. PR #1 still open,
not merged. The v2 gap addendum (D1–D7) has no repo copy — it lives
only in `~/workspace/xploclone/VOICE-CLONING-SKILL-GAPS.md`; no repo
file was invented for it.

## Skill-v2 improvements round — D1–D7 (2026-10-31)

From the voice-cloning skill v2 gap addendum (D1–D7). No LoRA, no
Urdu GPU work, no Xplogent integration, no merge.

- **D1 acoustic diagnosis:** new `scripts/benchmark/acoustic_profile.py`
  (numpy only by default, librosa/pyin optional, exits 2 naming
  librosa if `--f0-method pyin` without it; unmeasurable = `null`,
  never 0) + `tests/test_acoustic_profile.py` (19 tests). Reports
  mean F0, F0 SD/range (st), jitter/shimmer, HNR, H1–H2, speaking
  rate, pause/breath audit; compare mode gives clone−reference
  deltas. Documented in `docs/BENCHMARK.md` (§ Acoustic profile).
- **D5 too-clean check:** compare-mode flags — jitter/shimmer
  < 0.5× reference, HNR > ref + 3 dB, F0 SD < 1.5 st or < 0.5× ref,
  clone breath 0% while the reference has breaths. Row + subsection
  added to `docs/BENCHMARK.md`.
- **D2/D3 recording scripts:** `docs/recording-scripts/en-us.md`,
  `en-gb.md`, `ur.md` gained a §0 sustained-vowel baseline
  (/a, i, u/ 3–5 s, modal/breathy/creaky × 3 takes, per-take acoustic
  log) and a systematic prosody block (statements, yes/no + wh
  questions, lists, contrastive focus, long/short sentences, same
  sentence at ~120/150/180 wpm, breath groups, emotion by scenario
  with acoustic targets). Accent minimal sets verified unchanged.
- **D4 Urdu diacritics:** every Urdu script line must carry full
  diacritics + Roman/IPA gloss, homographs disambiguated before
  recording (PronouncUR ~64% on undiacritised text). Added to
  `ur.md` and as a standing rule in `docs/URDU-SPIKE.md` (verdict
  unchanged). Caveat: the pre-existing §§A–F lines in `ur.md` are
  NOT yet vocalised — deliberately left for the owner/recording
  pass; a wrongly placed diacritic would mislead the recording.
- **D6 telephony:** `docs/ARCHITECTURE.md` Phase 3 section states
  G.711 keeps 300–3,400 Hz only and "identity must survive in
  300 Hz–3.4 kHz — test SIM and listener identity *through* μ-law,
  not just on 24 kHz WAV"; PerTh-through-μ-law explicitly
  UNVERIFIED (`perth-unverified` kept).
- **D7 citations:** `docs/BENCHMARK.md` corrected — TTSDS2 over
  11,000 ratings (not ~11,800), ρ −0.11 to −0.45 is the expected
  sign for an error metric; long-form drift Qwen3-TTS 0.780 → 0.560
  over 0–210 s (Lim et al., Oct 2026), "~0.80 → ~0.52" labelled an
  approximate model-specific illustration.
- **500M blind-test prep:** new `docs/BENCHMARK-500M-BLIND-TEST.md`
  — Turbo vs full 500M vs ElevenLabs v4 Turbo, same script/reference,
  blind protocol, scoring sheet, Gate 1 criteria. Prep only: 500M
  synthesis NOT run here (needs GPU; Turbo ignores exaggeration/CFG,
  full 500M honours them — the reason for the test).

Verification (this VM, 2026-10-31): `pytest -q` **124 passed,
1 skipped** (was 105; +19 acoustic-profile tests). `ruff check` +
`ruff format --check` pass, `mypy api` clean (15 files),
`npm run typecheck` + `npm run build` pass (12 routes).
Acoustic profile re-run by the coordinator on the Phase A samples
(librosa pyin): api-en-us-his-voice.wav — mean F0 255.4 Hz, F0 SD
1.97 st, jitter 1.07%, shimmer 36.7%, HNR 10.39 dB, H1–H2 3.81 dB,
articulation 4.4 syll/s, 1 pause (3.27%, 0% breath). Compare mode
(ref en-us vs API en-us) fires `f0_flat` (clone SD 1.97 vs ref
4.62 st) — INVALID as a D5 result (different texts); it only
exercises the code path. Shimmer 36.7% is far above clinical
local-shimmer bands: treat it as a relative signal until the
estimator is cross-checked against Parselmouth/Praat.
