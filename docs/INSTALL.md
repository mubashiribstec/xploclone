# Install — XploClone

## One-click (recommended)

```bash
./install.sh            # auto: GPU if nvidia-smi works, else CPU
./install.sh --gpu      # GPU mode (Turbo, CUDA 13.0)
./install.sh --cpu      # CPU mode (Nano, file generation only)
./install.sh --check-only   # preflight only, changes nothing
./install.sh --dry-run      # show what would run, do not run Docker
```

Then open **http://localhost:3000/login**. The installer prints the
web password **once** — save it. It is never written to disk in
plaintext. After login, Generate works only once reference clips are
in place (below); until then voices report "unavailable", which is
correct.

Windows (PowerShell 5.1+, Docker Desktop with WSL 2):
```powershell
.\install.ps1            # auto-detect
.\install.ps1 -Mode cpu
```
Or double-click `install.bat`. **Windows installer is NOT tested**
(no Windows host in this environment) — the Linux `install.sh` is
the tested path. If it fails, use the manual install below and report
the exact error.

What the installer does: checks Docker + Compose, checks for an
NVIDIA GPU (warns, does not fail, if none), creates `.env` with fresh
random secrets (API key + hash, web password hash, session secret),
creates `api/reference/`, runs the right compose profile, and waits
for `http://127.0.0.1:8000/health` (up to 180 s).

## Manual install

### GPU mode
```bash
cp .env.example .env
# Generate real secrets (never reuse a shipped key):
python3 -c "import secrets; print(secrets.token_hex(32))"        # API key
python3 -c "import hashlib; print(hashlib.sha256(b'YOUR_KEY').hexdigest())"  # its hash
python3 -c "import hashlib; print(hashlib.sha256(b'YOUR_WEB_PASSWORD').hexdigest())"
python3 -c "import secrets; print(secrets.token_hex(32))"        # session secret
# Put the values in .env (see .env.example for the variable names).
docker compose up --build -d
curl http://127.0.0.1:8000/health
```

### CPU mode (test only)
```bash
cp .env.example .env   # fill in secrets as above, then:
# In .env set: XPLOCLONE_DEVICE=cpu  XPLOCLONE_ENGINE=nano  XPLOCLONE_TORCH_THREADS=8
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up --build -d
```
CPU mode uses `Dockerfile.cpu` (Python 3.14 + torch 2.14.1 CPU wheel,
verified to exist for cp314 on the CPU index, 2026-10-30) and Nano.
It is file generation only — never live calls. See
`docs/PC-REQUIREMENTS.md` Tier A.

### Dev without Docker (API logic only, no voice)
```bash
uv sync --python 3.14
uv run uvicorn api.main:app --reload --port 8000
curl localhost:8000/health
```
The API starts and tests without a GPU (engine is lazy-loaded).
Without recordings, voices report "unavailable" and `/v1/tts`
returns 503 — correct behaviour.

## Reference recordings (required for any voice)

Place clips in `api/reference/` (gitignored, never commit them):
`mubashir-en-us.wav`, `mubashir-en-gb.wav` — 48 kHz, 16-bit, mono WAV.
Start with a **60-second proxy** per variant to unblock testing, then
the full 20-minute set. Scripts: `docs/recording-scripts/`.
After adding clips, restart the API: `docker compose restart api`.
Urdu: **do not** place `mubashir-ur.wav` — the Urdu engine is gated
(`docs/URDU-SPIKE.md`); the API returns 503 for Urdu until it passes.

## Updating

```bash
git pull            # on the branch you are tracking
docker compose up --build -d
```
`.env` is never overwritten by the installer. If you re-run
`./install.sh` with an existing `.env`, it keeps your secrets.

## Uninstall / stop

```bash
docker compose down            # stop, keep images + .env
docker compose down -v --rmi all  # also remove images (models re-download on next up)
```

## Troubleshooting

See `docs/TROUBLESHOOTING.md`. The common cases: Docker missing,
GPU not found in Docker, voices "unavailable" (no clips), 401
(wrong/missing key), 503 `engine_unavailable` (Urdu / no engine),
slow CPU (expected — Nano on a 2-core VM is slower than real-time).
