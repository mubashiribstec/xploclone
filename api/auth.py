"""API-key authentication — hashed keys, single admin (PLAN-v2 §3.2/§10).

- The server only ever stores/compares the SHA-256 hex of the admin key
  (``XPLOCLONE_API_KEY_HASH``). The plaintext key is never written to disk
  by this service and never appears in logs.
- Comparison is constant-time (``hmac.compare_digest``).
- ``/health``, ``/metrics`` and ``GET /v1/voices`` are public (no secrets
  in their responses). ``POST /v1/tts`` requires a valid key.
- If no key hash is configured, TTS is refused unless the operator
  explicitly sets ``XPLOCLONE_ALLOW_NO_AUTH=1`` (local dev only).
"""

from __future__ import annotations

import hashlib
import hmac

from fastapi import HTTPException, Request

from .config import SETTINGS


def hash_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def _bearer_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    token = auth[7:].strip()
    return token or None


def require_api_key(request: Request) -> None:
    """Raise 401 unless the request carries the admin API key."""
    if not SETTINGS.api_key_hash and SETTINGS.allow_no_auth:
        return
    if not SETTINGS.api_key_hash:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "auth_not_configured",
                "message": "No API key is configured on this server.",
            },
        )
    token = _bearer_token(request)
    if token is None or not hmac.compare_digest(hash_key(token), SETTINGS.api_key_hash):
        raise HTTPException(
            status_code=401,
            detail={"code": "unauthorized", "message": "Invalid or missing API key."},
        )
