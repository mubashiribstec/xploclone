# Troubleshooting — XploClone

Run the doctor first: `python3 scripts/doctor.py` (or
`./install.sh --check-only`). It prints CPU/RAM/disk/GPU/Docker/
.env/reference-clip status and never prints a secret value.

## Install / Docker

**"Docker is not installed" / `docker: command not found`**
Install Docker (Linux: docker.com/get-docker; Windows: Docker
Desktop with WSL 2; macOS: Docker Desktop), then re-run
`./install.sh`. The installer fails clearly instead of pretending.

**GPU mode fails with a GPU / nvidia error**
Check: `nvidia-smi` works on the host? Is
`nvidia-container-toolkit` installed? Is the driver CUDA 13.0
capable (R570+)? The API image needs CUDA 13.0 (BUILD-LOG D1 —
torch 2.14.1 has no cu128 wheel). If the host cannot do CUDA 13.0,
use CPU mode (`./install.sh --cpu`) or a cloud GPU with a newer
driver. Do NOT silently downgrade torch — that is a recorded
decision, not a fix.

**"GPU reservation on CPU" — CPU compose still asks for a GPU**
`docker-compose.cpu.yml` replaces the base file's GPU reservation
with an empty devices list. If your Compose version does not
honour that override, remove the `deploy.resources.reservations`
block from `docker-compose.yml` for the CPU run, or run the API
without Docker (`uv run uvicorn api.main:app --port 8000` with
`XPLOCLONE_DEVICE=cpu XPLOCLONE_ENGINE=nano`).

**`docker compose up` fails on the web build**
Check Node/npm: the web image builds with Node 26.12.1. Run
`npm ci && npm run build` in `web/` locally to see the real error.
Common cause: a stale `web/node_modules` — delete it and retry.

**Healthcheck fails / API restarts in a loop**
The healthcheck calls `/health` (5 s timeout). A long synthesis
no longer blocks `/health` (M2 fix), but a *cold model load* can
take minutes on CPU — the CPU compose file allows a 180 s
start-period. Check logs: `docker compose logs api`. If the log
says the engine failed to load, see "Engine fails to load" below.

## Voices / engine

**Voices report "unavailable" / `/v1/tts` returns 503 `engine_unavailable`**
This is correct if there is no reference clip: place
`api/reference/mubashir-en-us.wav` and `mubashir-en-gb.wav`
(48 kHz, 16-bit, mono), then `docker compose restart api`.
Check with `python3 scripts/doctor.py` — it lists which clips
are present. Urdu always returns 503 until the gated spike
passes (`docs/URDU-SPIKE.md`) — never a silent fallback.

**Engine fails to load ("Chatterbox Turbo failed to load")**
Check the server logs for the real error (clients get only the
generic message). Common causes: no internet for the first Hugging
Face download, wrong revision pin, out of VRAM/RAM. The pinned
Turbo revision is `749d1c1a46eb10492095d68fbcf55691ccf137cd`;
Nano's revision is unpinned by default — `/health` shows the
resolved commit; pin it before Gate 1.

**Slow CPU generation**
Expected. Nano on an 8-core CPU is vendor-claimed 3× real-time;
on a 2-core VM it is slower than real-time, and Turbo on CPU is
slower still. CPU mode is file generation only — never live calls.
If a single short sentence takes minutes, check
`XPLOCLONE_TORCH_THREADS` (set 8 on an 8-core host) and that you
are actually on Nano (`/health` shows `"engine": "nano"`).

**A truncated pcm16 stream**
Treat a stream that ends early as a failure, not as audio, and
retry. The server logs the real error server-side.

## Auth / API

**401 on POST /v1/tts**
Missing or wrong `Authorization: Bearer <key>`. The key in
`.env` (`XPLOCLONE_API_KEY`) must hash to `XPLOCLONE_API_KEY_HASH`
— regenerate both together with `./install.sh` (fresh `.env`) or
the commands in `.env.example`. Note: the web UI uses its own
password, not the API key.

**Web UI: login fails / redirected to /login in a loop**
`XPLOCLONE_WEB_PASSWORD_HASH` and `XPLOCLONE_WEB_SESSION_SECRET`
must both be set in `.env` (the installer generates them). With
either empty, logins are refused by design. The password printed
once by `./install.sh` is the only copy — if you lost it, generate
a new hash and restart the web service.

**429 rate limit / 503 engine_busy**
60 req/min per key (429, Retry-After header) or the synthesis
queue is full (503 `engine_busy`, Retry-After: 5). Wait and retry;
do not hammer the endpoint — one synthesis runs at a time.

## CI

**No CI runs on PR #1**
Expected: `.github/workflows/ci.yml` cannot be pushed by the
GitHub App (no `workflows` permission). It must be committed from
a real git checkout after merge. Do not claim CI is green on
GitHub until a green run exists on `main`.

## Still stuck?

Collect: `python3 scripts/doctor.py` output, `docker compose logs api`
(last 50 lines), the exact command you ran, and the exact error.
Do NOT paste secrets, API keys, or `.env` contents anywhere.
