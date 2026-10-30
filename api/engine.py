"""Engine layer — Chatterbox Turbo for English, nothing for Urdu (yet).

Verified against chatterbox-tts 0.1.7 (wheel inspected 2026-10-30):
- ``from chatterbox.tts_turbo import ChatterboxTurboTTS``
- ``ChatterboxTurboTTS.from_pretrained(device)`` downloads
  ``ResembleAI/chatterbox-turbo`` (MIT, English only);
  ``from_local(ckpt_dir, device)`` loads a pinned local copy.
- ``generate(text, audio_prompt_path=...)`` returns a torch tensor of
  24 kHz audio (``S3GEN_SR = 24000``) and applies the PerTh implicit
  watermark inside ``generate()`` — the watermark is preserved by
  design; this code never strips it and never re-encodes lossily.
- ``REPO_ID = "ResembleAI/chatterbox-turbo"`` in the 0.1.7 source.

The import of ``chatterbox`` is LAZY (inside ``load()``) so the API can
start, answer /health, and run its unit tests on a CPU-only machine with
no GPU and no torch installed. GPU inference was NOT tested in this
environment — see docs/BUILD-LOG.md.

Urdu: there is deliberately no engine class here. ``mubashir-ur`` resolves
to ``EngineUnavailable`` until the gated spike (docs/URDU-SPIKE.md)
passes and an engine is wired in. Never fall back to English.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .audio import SAMPLE_RATE
from .config import SETTINGS
from .voices import ENGLISH_VOICE_IDS, URDU_VOICE_ID


class EngineUnavailable(Exception):
    """Raised when a voice has no loaded engine. Maps to 503."""

    def __init__(self, voice_id: str, reason: str) -> None:
        super().__init__(reason)
        self.voice_id = voice_id
        self.reason = reason
        self.code = "engine_unavailable"


@dataclass
class SynthesisResult:
    pcm16: bytes
    sample_rate: int = SAMPLE_RATE
    latency_ms: float = 0.0
    watermark: str = "perth-preserved"
    chunks: int = 1


@dataclass
class EngineRegistry:
    """Holds the loaded engines and the reference-clip paths."""

    ref_dir: Path = field(default_factory=lambda: Path(SETTINGS.ref_dir))
    device: str = SETTINGS.device
    revision: str = SETTINGS.chatterbox_revision
    _turbo: Any = None
    _loaded: bool = False
    _load_error: str | None = None

    def reference_path(self, voice_id: str) -> Path:
        return self.ref_dir / f"{voice_id}.wav"

    def has_reference(self, voice_id: str) -> bool:
        path = self.reference_path(voice_id)
        return path.is_file() and path.stat().st_size > 0

    def status(self, voice_id: str) -> str:
        """'loaded' | 'unavailable' — as reported by GET /v1/voices."""
        if voice_id == URDU_VOICE_ID:
            return "unavailable"
        if voice_id in ENGLISH_VOICE_IDS:
            return "loaded" if (self._loaded and self.has_reference(voice_id)) else "unavailable"
        return "unavailable"

    def load_english(self) -> None:
        """Load Chatterbox Turbo once. Safe to call repeatedly."""
        if self._loaded:
            return
        try:
            from chatterbox.tts_turbo import ChatterboxTurboTTS  # lazy, GPU-only

            self._turbo = ChatterboxTurboTTS.from_pretrained(device=self.device)
            self._loaded = True
        except Exception as exc:  # noqa: BLE001 — record, do not crash startup
            self._load_error = f"{type(exc).__name__}: {exc}"
            self._loaded = False

    def synthesize(self, voice_id: str, chunks: list[str]) -> SynthesisResult:
        """Synthesise chunked text in one voice. Returns concatenated PCM16."""
        if voice_id == URDU_VOICE_ID:
            raise EngineUnavailable(
                voice_id,
                "Urdu engine is not loaded. The Urdu spike has not passed yet "
                "(see docs/URDU-SPIKE.md). No fallback voice is used.",
            )
        if voice_id not in ENGLISH_VOICE_IDS:
            raise EngineUnavailable(voice_id, f"Unknown voice: {voice_id}")
        if not self.has_reference(voice_id):
            raise EngineUnavailable(
                voice_id,
                f"No reference recording for {voice_id} in {self.ref_dir}. "
                "Record the 20-minute set (docs/recording-scripts/) and place "
                f"{voice_id}.wav there. Proxy: a 60-second clip unblocks testing.",
            )
        self.load_english()
        if not self._loaded or self._turbo is None:
            raise EngineUnavailable(
                voice_id,
                f"Chatterbox Turbo failed to load: {self._load_error or 'unknown error'}",
            )
        started = time.monotonic()
        pcm_parts: list[bytes] = []
        turbo = self._turbo
        ref = str(self.reference_path(voice_id))
        for chunk in chunks:
            wav = turbo.generate(chunk, audio_prompt_path=ref)
            arr = wav.squeeze(0).detach().cpu().numpy()
            pcm_parts.append((arr * 32767).astype("int16").tobytes())
        latency_ms = (time.monotonic() - started) * 1000.0
        return SynthesisResult(
            pcm16=b"".join(pcm_parts),
            sample_rate=SAMPLE_RATE,
            latency_ms=latency_ms,
            watermark="perth-preserved",
            chunks=len(chunks),
        )


REGISTRY = EngineRegistry()
