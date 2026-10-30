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
    ref_dir: str = os.environ.get("XPLOCLONE_REF_DIR", "api/reference")
    chatterbox_revision: str = os.environ.get(
        "XPLOCLONE_CHATTERBOX_REVISION",
        "749d1c1a46eb10492095d68fbcf55691ccf137cd",
    )
    rate_limit_per_min: int = _int_env("XPLOCLONE_RATE_LIMIT_PER_MIN", 60)
    queue_max: int = _int_env("XPLOCLONE_QUEUE_MAX", 10)
    request_timeout_s: int = _int_env("XPLOCLONE_REQUEST_TIMEOUT_S", 30)
    max_chars: int = _int_env("XPLOCLONE_MAX_CHARS", 5000)
    # When 1, the API starts without an API key hash (local dev only).
    # Production must always set XPLOCLONE_API_KEY_HASH.
    allow_no_auth: bool = os.environ.get("XPLOCLONE_ALLOW_NO_AUTH", "0") == "1"


SETTINGS = Settings()
