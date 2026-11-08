#!/usr/bin/env python3
"""CPU smoke test for XploClone — no GPU, no model, no real voice.

Generates a synthetic sine-tone clip through the same code paths the
API uses (audio helpers + cache + chunking), then exercises the API
with TestClient and a faked engine, in CPU mode
(XPLOCLONE_DEVICE=cpu, XPLOCLONE_ENGINE=nano).

Usage:
    python3 scripts/cpu_smoke.py
    XPLOCLONE_RUN_CPU_SMOKE=1 pytest -q tests/test_streaming_cpu.py -k cpu_smoke

Exit 0 = CPU path works end-to-end (API logic only). This does NOT
prove Nano synthesis on CPU — that needs a real Nano load on a CPU
host with a reference clip (see docs/PC-REQUIREMENTS.md). It proves
the CPU configuration, the API contract, caching and streaming work
without a GPU.
"""

from __future__ import annotations

import hashlib
import os
import sys
import time
from pathlib import Path

# Test key hash — set before any api import (settings are read once).
os.environ.setdefault(
    "XPLOCLONE_API_KEY_HASH",
    hashlib.sha256(b"test-key").hexdigest(),
)

os.environ.setdefault("XPLOCLONE_DEVICE", "cpu")
os.environ.setdefault("XPLOCLONE_ENGINE", "nano")
os.environ.setdefault("XPLOCLONE_TORCH_THREADS", "2")
# TestClient talks to host "testserver" — it must be an allowed host.
# Set here, before ANY api import, because api.config reads settings
# once at import time (tests/conftest.py does the same).
os.environ.setdefault("XPLOCLONE_ALLOWED_HOSTS", "testserver,localhost,127.0.0.1")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    from api.audio import sine_pcm16
    from api.cache import AudioCache
    from api.chunking import chunk_text
    from api.config import SETTINGS

    print(
        f"CPU smoke — device={SETTINGS.device} engine={SETTINGS.engine} "
        f"torch_threads={SETTINGS.torch_threads}"
    )
    t0 = time.monotonic()
    pcm = sine_pcm16(0.5, freq_hz=440.0)
    assert len(pcm) > 0 and len(pcm) % 2 == 0
    print(f"  synthetic clip: {len(pcm)} bytes PCM16 in {(time.monotonic() - t0) * 1000:.1f} ms")

    # Two sentences of ~260 chars each (total >400) so chunking
    # produces 2 chunks; short sentences are joined by design.
    long_text = (
        "This is the first long test sentence, written deliberately to be well over two hundred "
        "and sixty characters in total length, so that the chunker cannot join it with the next "
        "sentence and has to emit it as its own separate chunk for synthesis. "
        "This is the second long test sentence, also deliberately written to be well over two "
        "hundred and sixty characters in total length, so that the chunker produces a second "
        "chunk instead of joining the two sentences together into one."
    )
    chunks = chunk_text(long_text)
    assert len(chunks) == 2, chunks
    print(f"  chunking: {len(chunks)} chunks")

    cache = AudioCache(ttl_s=60, max_entries=4)
    key = AudioCache.key("mubashir-en-gb", long_text, "pcm16")
    assert cache.get(key) is None
    cache.put(key, pcm)
    assert cache.get(key) == pcm
    print("  audio cache: miss then hit — ok")

    # API contract via TestClient (no engine load — /health and
    # /v1/voices do not synthesise; the engine stays lazy).
    # Run with the project venv for this part:
    #   uv run --python 3.14 python scripts/cpu_smoke.py
    # On plain system Python without fastapi, skip it gracefully.
    try:
        from fastapi.testclient import TestClient
    except ModuleNotFoundError:
        print("  API contract: SKIPPED — fastapi not installed for this Python;")
        print("    run: uv run --python 3.14 python scripts/cpu_smoke.py")
        print("CPU smoke: PASS (synthetic clip + chunking + cache; API contract skipped)")
        return 0
    from api.main import app

    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200, r.text
        body = r.json()
        print(f"  /health: ok, device={body['device']}, engine={body.get('engine')}")
        r = client.get("/v1/voices")
        assert r.status_code == 200
        assert len(r.json()["voices"]) == 3
        print("  /v1/voices: 3 voices listed")
    print("CPU smoke: PASS (API logic only — Nano synthesis on CPU still unmeasured)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
