"""Shared fixtures: a test client with auth enabled and a fake engine.

The real Chatterbox engine is never imported in tests (no GPU, no torch).
``REGISTRY.synthesize`` is monkeypatched to return a short sine tone.
"""

from __future__ import annotations

import hashlib
import os

os.environ["XPLOCLONE_API_KEY_HASH"] = hashlib.sha256(b"test-key").hexdigest()
os.environ["XPLOCLONE_ALLOW_NO_AUTH"] = "0"
os.environ["XPLOCLONE_REF_DIR"] = "/tmp/xploclone-test-ref"
# TestClient talks to host "testserver" — it must be an allowed host (m17).
os.environ["XPLOCLONE_ALLOWED_HOSTS"] = "testserver,localhost,127.0.0.1"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.audio import sine_pcm16  # noqa: E402
from api.engine import REGISTRY, SynthesisResult  # noqa: E402
from api.main import app  # noqa: E402

AUTH = {"Authorization": "Bearer test-key"}


@pytest.fixture()
def client(monkeypatch):  # type: ignore[no-untyped-def]
    def fake_synthesize(voice_id: str, chunks: list[str]) -> SynthesisResult:
        # Urdu must still fail even with a fake engine — the router rejects it.
        from api.engine import EngineUnavailable

        if voice_id == "mubashir-ur":
            raise EngineUnavailable(voice_id, "Urdu engine is not loaded.")
        return SynthesisResult(pcm16=sine_pcm16(0.1), chunks=len(chunks))

    def fake_synthesize_one(voice_id: str, chunk: str) -> bytes:
        # Per-sentence streaming path (pcm16): same fake tone per chunk.
        if voice_id == "mubashir-ur":
            from api.engine import EngineUnavailable

            raise EngineUnavailable(voice_id, "Urdu engine is not loaded.")
        return sine_pcm16(0.1)

    def fake_ensure_loaded(voice_id: str) -> None:
        if voice_id == "mubashir-ur":
            from api.engine import EngineUnavailable

            raise EngineUnavailable(voice_id, "Urdu engine is not loaded.")

    monkeypatch.setattr(REGISTRY, "synthesize", fake_synthesize)
    monkeypatch.setattr(REGISTRY, "synthesize_one", fake_synthesize_one)
    monkeypatch.setattr(REGISTRY, "ensure_loaded", fake_ensure_loaded)
    monkeypatch.setattr(REGISTRY, "has_reference", lambda voice_id: voice_id != "mubashir-ur")
    with TestClient(app) as test_client:
        yield test_client
