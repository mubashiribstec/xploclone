#!/usr/bin/env bash
# XploClone — one-click install (Linux / macOS).
#
#   ./install.sh            # auto-detect: GPU if nvidia-smi works, else CPU
#   ./install.sh --gpu      # GPU mode (Chatterbox Turbo, CUDA 13.0)
#   ./install.sh --cpu      # CPU mode (Chatterbox Nano, file generation only)
#   ./install.sh --check-only   # preflight checks only, no Docker, no .env changes
#   ./install.sh --dry-run      # show what would run, do not run Docker
#   ./install.sh --help
#
# What it does:
#   1. Checks Docker + Docker Compose (fails clearly if missing).
#   2. Checks for an NVIDIA GPU (warns, does not fail, if none).
#   3. Creates .env (if missing) with REAL random secrets — API key +
#      hash, web password hash + session secret. The web password is
#      printed ONCE to the terminal; save it. It is never written to
#      disk in plaintext and never shipped in the repo.
#   4. Creates api/reference/ for your recordings (gitignored).
#   5. Runs the right compose profile and waits for /health.
#
# After it finishes: open http://localhost:3000/login and log in with
# the printed web password. Without reference recordings the voices
# report "unavailable" — that is correct, not a bug (see docs/INSTALL.md).
# Place clips in api/reference/ (mubashir-en-us.wav, mubashir-en-gb.wav).
#
# This script was tested with --help / --check-only / --dry-run on a
# CPU-only VM with no Docker (2026-10-30): it fails clearly with the
# Docker install instructions instead of pretending to install.
# A full Docker run was NOT tested in this environment (no Docker here).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

MODE="auto"          # auto | cpu | gpu
CHECK_ONLY=0
DRY_RUN=0

log() { printf '[xploclone] %s\n' "$*"; }
warn() { printf '[xploclone] WARNING: %s\n' "$*" >&2; }
die() { printf '[xploclone] ERROR: %s\n' "$*" >&2; exit 1; }

usage() {
  sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

for arg in "$@"; do
  case "$arg" in
    --help|-h) usage ;;
    --cpu) MODE="cpu" ;;
    --gpu) MODE="gpu" ;;
    --check-only) CHECK_ONLY=1 ;;
    --dry-run) DRY_RUN=1 ;;
    *) die "Unknown argument: $arg (try ./install.sh --help)" ;;
  esac
done

# --- helpers ---------------------------------------------------------------
hex_secret() { # $1 = bytes
  if command -v python3 >/dev/null 2>&1; then
    python3 -c "import secrets; print(secrets.token_hex($1))"
  elif command -v openssl >/dev/null 2>&1; then
    openssl rand -hex "$1"
  else
    head -c "$(( $1 * 2 ))" /dev/urandom | od -An -tx1 | tr -d ' \n'
    echo
  fi
}

sha256_hex() { # $1 = plaintext (passed via stdin-safe printf, not argv in logs)
  if command -v python3 >/dev/null 2>&1; then
    python3 -c "import hashlib,sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest())" "$1"
  else
    printf '%s' "$1" | sha256sum | cut -d' ' -f1
  fi
}

detect_compose() {
  if docker compose version >/dev/null 2>&1; then
    echo "docker compose"
  elif command -v docker-compose >/dev/null 2>&1; then
    echo "docker-compose"
  else
    echo ""
  fi
}

# --- preflight -------------------------------------------------------------
log "Preflight checks (repo: $REPO_DIR)"
CPU_CORES="$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo "?")"
log "CPU cores: $CPU_CORES"
if command -v docker >/dev/null 2>&1; then
  log "Docker: $(docker --version 2>/dev/null || echo "installed (version unknown)")"
else
  warn "Docker is not installed."
  if [ "$DRY_RUN" -eq 1 ]; then
    log "[dry-run] Docker is missing, but dry-run only shows what would run — continuing."
    COMPOSE="docker compose"
  elif [ "$CHECK_ONLY" -eq 1 ]; then
    log "check-only: stopping here (Docker is required for a real install)."
    echo "Install Docker first: https://docs.docker.com/get-docker/ then re-run ./install.sh"
    exit 1
  else
    die "Docker is required. Install it first: https://docs.docker.com/get-docker/ then re-run ./install.sh"
  fi
fi
if [ "$DRY_RUN" -eq 0 ]; then
  COMPOSE="$(detect_compose)"
  if [ -z "$COMPOSE" ]; then
    die "Docker Compose was not found. Install Docker Desktop / docker compose plugin, then re-run."
  fi
  log "Compose: $COMPOSE"
fi

HAS_GPU=0
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
  HAS_GPU=1
  log "NVIDIA GPU detected:"
  nvidia-smi -L | sed 's/^/[xploclone]   /'
  log "Note: the Docker NVIDIA runtime (nvidia-container-toolkit) is also required for GPU mode — if 'docker compose up' fails with a GPU error, install it, or use --cpu."
else
  warn "No NVIDIA GPU detected (nvidia-smi missing or no GPU). GPU mode will fail; CPU mode is the fallback."
fi

if [ "$MODE" = "auto" ]; then
  if [ "$HAS_GPU" -eq 1 ]; then MODE="gpu"; else MODE="cpu"; fi
  log "Mode auto-detected: $MODE"
else
  log "Mode: $MODE (explicit)"
fi
if [ "$MODE" = "gpu" ] && [ "$HAS_GPU" -eq 0 ]; then
  warn "You asked for --gpu but no NVIDIA GPU was detected. Continuing anyway — Docker will fail clearly if the GPU is really absent. Use --cpu for CPU test mode."
fi
if [ "$MODE" = "cpu" ]; then
  log "CPU mode: Chatterbox Nano, file generation only, no live calls (see docs/PC-REQUIREMENTS.md)."
fi

if [ "$CHECK_ONLY" -eq 1 ]; then
  log "check-only: all checks above are the result. Nothing was changed."
  exit 0
fi

if [ "$DRY_RUN" -eq 1 ]; then
  COMPOSE="${COMPOSE:-docker compose}"
  if [ "$MODE" = "cpu" ]; then
    log "[dry-run] would run: $COMPOSE -f docker-compose.yml -f docker-compose.cpu.yml up --build -d"
  else
    log "[dry-run] would run: $COMPOSE -f docker-compose.yml up --build -d"
  fi
  log "[dry-run] then wait for http://127.0.0.1:8000/health and open http://localhost:3000/login"
  log "[dry-run] no .env was created and nothing was started."
  exit 0
fi

# --- .env ------------------------------------------------------------------
WEB_PASSWORD=""
if [ ! -f .env ]; then
  log "Creating .env with fresh random secrets (never shipped in the repo)..."
  API_KEY="$(hex_secret 32)"
  API_KEY_HASH="$(sha256_hex "$API_KEY")"
  WEB_PASSWORD="$(hex_secret 8)"
  WEB_PASSWORD_HASH="$(sha256_hex "$WEB_PASSWORD")"
  SESSION_SECRET="$(hex_secret 32)"
  if [ "$MODE" = "cpu" ]; then
    ENGINE="nano"; DEVICE="cpu"; THREADS="8"
  else
    ENGINE="turbo"; DEVICE="cuda"; THREADS="0"
  fi
  cat > .env <<EOF
# XploClone — generated by ./install.sh on $(date -u +%Y-%m-%d). NEVER commit .env.
# API key (plaintext, server-side proxy only) — keep this file private.
XPLOCLONE_API_KEY=$API_KEY
XPLOCLONE_API_KEY_HASH=$API_KEY_HASH
XPLOCLONE_DEVICE=$DEVICE
XPLOCLONE_ENGINE=$ENGINE
XPLOCLONE_TORCH_THREADS=$THREADS
XPLOCLONE_REF_DIR=api/reference
XPLOCLONE_CHATTERBOX_REVISION=749d1c1a46eb10492095d68fbcf55691ccf137cd
XPLOCLONE_CHATTERBOX_NANO_REVISION=
XPLOCLONE_RATE_LIMIT_PER_MIN=60
XPLOCLONE_QUEUE_MAX=10
XPLOCLONE_REQUEST_TIMEOUT_S=30
XPLOCLONE_MAX_CHARS=5000
XPLOCLONE_API_URL=http://localhost:8000
XPLOCLONE_WEB_PASSWORD_HASH=$WEB_PASSWORD_HASH
XPLOCLONE_WEB_SESSION_SECRET=$SESSION_SECRET
EOF
  chmod 600 .env
  log ".env created (mode 600). Web password is printed once below — save it now."
else
  log ".env already exists — keeping it (never overwriting secrets)."
  # Fill in engine/device for the chosen mode if the operator agrees
  # by leaving existing values alone; install.sh does not rewrite .env.
  log "If .env still says XPLOCLONE_DEVICE=cuda on a CPU-only machine, edit it to cpu + nano (see docs/INSTALL.md)."
fi

mkdir -p api/reference
touch api/reference/.gitkeep 2>/dev/null || true

# --- up --------------------------------------------------------------------
if [ "$MODE" = "cpu" ]; then
  log "Starting CPU profile: $COMPOSE -f docker-compose.yml -f docker-compose.cpu.yml up --build -d"
  $COMPOSE -f docker-compose.yml -f docker-compose.cpu.yml up --build -d
else
  log "Starting GPU profile: $COMPOSE -f docker-compose.yml up --build -d"
  $COMPOSE -f docker-compose.yml up --build -d
fi

# --- wait for health -------------------------------------------------------
log "Waiting for the API (up to 180 s) at http://127.0.0.1:8000/health ..."
for _ in $(seq 1 36); do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
    log "API is up."
    break
  fi
  sleep 5
done
curl -fsS http://127.0.0.1:8000/health || warn "API did not answer /health yet — check: $COMPOSE logs api"
curl -fsS http://127.0.0.1:8000/v1/voices || true

echo
log "Done. Mode: $MODE"
log "Web UI:  http://localhost:3000/login"
log "API:     http://127.0.0.1:8000/health"
if [ -n "$WEB_PASSWORD" ]; then
  echo
  echo "  *** SAVE THIS — it is printed once and never stored in plaintext ***"
  echo "  Web UI password: $WEB_PASSWORD"
  echo
fi
log "Next: place reference clips in api/reference/ (mubashir-en-us.wav, mubashir-en-gb.wav), then restart: $COMPOSE restart api"
log "Docs: docs/INSTALL.md, docs/USER-GUIDE.md, docs/TROUBLESHOOTING.md"
