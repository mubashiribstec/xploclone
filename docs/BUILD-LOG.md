# XploClone — Build log (Phase 0 + Phase 1, branch `muse/xploclone-mvp`)

Date: 2026-10-30. Implementer: Muse (subagent). Plan: PLAN-v2 (authoritative).

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
