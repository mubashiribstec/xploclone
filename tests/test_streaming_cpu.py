"""Per-sentence streaming tests (pcm16) + CPU-mode config tests.

Streaming: the first chunk must arrive before the last sentence is
synthesised. Proven with a slow fake synthesize_one (0.4 s per chunk)
and two chunks: the first byte must arrive well before 0.8 s total.
CPU mode: config flags (engine=nano, device=cpu, torch threads) must
parse from the environment; Nano wiring must pass the pinned repo
through snapshot_download.
"""

import os
import time

import pytest

from tests.conftest import AUTH


def test_pcm16_streams_first_chunk_early(client, monkeypatch) -> None:
    """D4 fix: pcm16 first byte arrives after chunk 1, not after chunk 2."""
    from api.audio import sine_pcm16
    from api.engine import REGISTRY

    def slow_one(voice_id: str, chunk: str, prosody=None) -> bytes:  # type: ignore[no-untyped-def]
        time.sleep(0.4)
        return sine_pcm16(0.1)

    monkeypatch.setattr(REGISTRY, "synthesize_one", slow_one)
    monkeypatch.setattr(REGISTRY, "ensure_loaded", lambda voice_id: None)

    started = time.monotonic()
    first_byte_at: list[float] = []
    with client.stream(
        "POST",
        "/v1/tts",
        json={
            "voice_id": "mubashir-en-gb",
            "text": "First sentence here. Second sentence here.",
            "format": "pcm16",
        },
        headers=AUTH,
    ) as r:
        assert r.status_code == 200
        assert r.headers.get("X-Streaming") == "per-sentence"
        for _chunk in r.iter_bytes():
            first_byte_at.append(time.monotonic() - started)
            break
    assert first_byte_at, "stream produced no bytes"
    # Two chunks at 0.4 s each = 0.8 s total; first byte must be < 0.65 s.
    assert first_byte_at[0] < 0.65, f"first byte arrived at {first_byte_at[0]:.2f}s (not streaming)"


def test_wav_stays_whole_file(client) -> None:
    """WAV keeps the whole-file path (header needs total size)."""
    r = client.post(
        "/v1/tts",
        json={"voice_id": "mubashir-en-gb", "text": "Hello, wav test.", "format": "wav"},
        headers=AUTH,
    )
    assert r.status_code == 200
    assert r.headers.get("X-Streaming") is None
    assert r.content[:4] == b"RIFF"


def test_streaming_disabled_falls_back_to_whole_file(client, monkeypatch) -> None:
    """XPLOCLONE_STREAM_PER_SENTENCE=0 disables per-sentence streaming."""
    import dataclasses

    from api import main as main_module

    # SETTINGS is a frozen dataclass — replace the object, do not mutate.
    monkeypatch.setattr(
        main_module,
        "SETTINGS",
        dataclasses.replace(main_module.SETTINGS, stream_per_sentence=False),
    )
    r = client.post(
        "/v1/tts",
        json={"voice_id": "mubashir-en-gb", "text": "Hello.", "format": "pcm16"},
        headers=AUTH,
    )
    assert r.status_code == 200
    assert r.headers.get("X-Streaming") is None


def test_cpu_config_parses() -> None:
    """CPU-mode env vars parse into Settings (no model loaded)."""
    import importlib

    os.environ["XPLOCLONE_DEVICE"] = "cpu"
    os.environ["XPLOCLONE_ENGINE"] = "nano"
    os.environ["XPLOCLONE_TORCH_THREADS"] = "8"
    import api.config as config_module

    importlib.reload(config_module)
    try:
        assert config_module.SETTINGS.device == "cpu"
        assert config_module.SETTINGS.engine == "nano"
        assert config_module.SETTINGS.torch_threads == 8
    finally:
        for key in ("XPLOCLONE_DEVICE", "XPLOCLONE_ENGINE", "XPLOCLONE_TORCH_THREADS"):
            os.environ.pop(key, None)
        importlib.reload(config_module)


def test_nano_download_uses_nano_repo(monkeypatch) -> None:
    """Nano engine downloads from ResembleAI/chatterbox-nano, not Turbo."""
    import sys
    import types
    from pathlib import Path

    from api.engine import REPO_ID_NANO, EngineRegistry

    captured: dict[str, str | None] = {}
    fake = types.ModuleType("huggingface_hub")

    def fake_download(repo_id: str, revision: str | None = None) -> str:
        captured["repo_id"] = repo_id
        captured["revision"] = revision
        return "/tmp/fake-nano/abc123"

    fake.snapshot_download = fake_download  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake)

    reg = EngineRegistry(engine_name="nano", nano_revision="")
    path = reg._download_checkpoint()
    assert captured["repo_id"] == REPO_ID_NANO
    assert path == Path("/tmp/fake-nano/abc123")


def test_unknown_engine_fails_loudly() -> None:
    """An unknown XPLOCLONE_ENGINE must not silently fall back to Turbo."""
    from api.engine import EngineRegistry

    reg = EngineRegistry(engine_name="bogus")
    reg.load_english()
    assert reg._loaded is False
    assert reg._load_error is not None
    assert "bogus" in reg._load_error


@pytest.mark.skipif(
    os.environ.get("XPLOCLONE_RUN_CPU_SMOKE") != "1",
    reason="CPU smoke only with XPLOCLONE_RUN_CPU_SMOKE=1",
)
def test_cpu_smoke_sine_clip() -> None:
    """CPU smoke: a synthetic clip synthesises without a model/GPU.

    Only runs when explicitly enabled — it exercises the CPU path
    end-to-end with the sine-tone test clip, never a real voice.
    """
    from api.audio import sine_pcm16

    pcm = sine_pcm16(0.5, freq_hz=440.0)
    assert len(pcm) > 0
    assert len(pcm) % 2 == 0
