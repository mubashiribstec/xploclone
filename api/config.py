"""Configuration for the XploClone API.

All settings come from the environment. No secrets are hard-coded.
The only API key material in this service is a SHA-256 *hash* of the admin
key (``XPLOCLONE_API_KEY_HASH``); the plaintext key is never stored here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Runtime settings, read once at startup."""

    api_key_hash: str = os.environ.get("XPLOCLONE_API_KEY_HASH", "")
    device: str = os.environ.get("XPLOCLONE_DEVICE", "cuda")
    # Engine: "turbo" (350M, GPU prod) or "nano" (110M, CPU test mode).
    # Nano is the same ChatterboxTurboTTS class with nano=True
    # (ResembleAI/chatterbox-nano, MIT, 10 s reference clip, vendor claim
    # 3x real-time on 8 CPU cores — unmeasured here, see
    # docs/OPEN-SOURCE-CLONERS-2026.md). Default turbo; CPU mode
    # (install.sh --cpu / docker-compose.cpu.yml) sets nano.
    engine: str = os.environ.get("XPLOCLONE_ENGINE", "turbo").lower()
    # Hugging Face revision pinned for the Nano weights. Pinned
    # 2026-10-31 to the snapshot commit actually downloaded and
    # tested on CPU/Nano (71ccd1d0081b430592cea481f4307e764e07bc64) —
    # the Nano weights must match the git-master chatterbox code
    # (see pyproject.toml). Turbo's revision is pinned by default
    # and must never be left empty.
    chatterbox_nano_revision: str = os.environ.get(
        "XPLOCLONE_CHATTERBOX_NANO_REVISION", "71ccd1d0081b430592cea481f4307e764e07bc64"
    )
    # Torch threads on CPU (0 = torch default, usually #cores). Set to 8
    # for Nano's vendor-claimed 3x real-time (8 threads).
    torch_threads: int = _int_env("XPLOCLONE_TORCH_THREADS", 0)
    # Per-sentence HTTP streaming for pcm16 (1 = on). WAV stays whole-file
    # (its header needs the total size up front); see api/main.py.
    stream_per_sentence: bool = os.environ.get("XPLOCLONE_STREAM_PER_SENTENCE", "1") == "1"
    # Identical-request audio cache (in-memory, per process). 0 disables.
    cache_ttl_s: int = _int_env("XPLOCLONE_AUDIO_CACHE_TTL_S", 3600)
    cache_max_entries: int = _int_env("XPLOCLONE_AUDIO_CACHE_MAX_ENTRIES", 32)
    ref_dir: str = os.environ.get("XPLOCLONE_REF_DIR", "api/reference")
    chatterbox_revision: str = os.environ.get(
        "XPLOCLONE_CHATTERBOX_REVISION",
        "749d1c1a46eb10492095d68fbcf55691ccf137cd",
    )
    rate_limit_per_min: int = _int_env("XPLOCLONE_RATE_LIMIT_PER_MIN", 60)
    queue_max: int = _int_env("XPLOCLONE_QUEUE_MAX", 10)
    request_timeout_s: int = _int_env("XPLOCLONE_REQUEST_TIMEOUT_S", 30)
    max_chars: int = _int_env("XPLOCLONE_MAX_CHARS", 5000)
    # Hosts allowed by TrustedHostMiddleware (m17). Same-origin via the
    # Next.js proxy only; direct browser calls are not supported.
    # "testserver" is added by tests/conftest.py for TestClient.
    allowed_hosts: tuple[str, ...] = tuple(
        h.strip()
        for h in os.environ.get("XPLOCLONE_ALLOWED_HOSTS", "localhost,127.0.0.1,api,web").split(",")
        if h.strip()
    )
    # Startup warmup (m7): load the English engine at startup so /health
    # reports readiness and the first request does not pay the full
    # model-load time. Off by default — CPU-only smoke tests start fast.
    warmup_on_startup: bool = os.environ.get("XPLOCLONE_WARMUP_ON_STARTUP", "0") == "1"
    # If 1 (and warmup is on, and a reference clip exists), also run one
    # short generation at startup to warm the generation path. Off by
    # default; the first real request still works without it.
    warmup_generate: bool = os.environ.get("XPLOCLONE_WARMUP_GENERATE", "0") == "1"
    # When 1, the API starts without an API key hash (local dev only).
    # Production must always set XPLOCLONE_API_KEY_HASH.
    allow_no_auth: bool = os.environ.get("XPLOCLONE_ALLOW_NO_AUTH", "0") == "1"


SETTINGS = Settings()
