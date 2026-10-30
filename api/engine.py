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

Revision pin (M3 fix): the pinned revision is ENFORCED, not just
recorded. ``load_english`` downloads the weights with
``snapshot_download(repo_id, revision=...)`` and loads them with
``from_local``; if the downloaded snapshot's commit does not equal the
pinned revision, startup/synthesis fails loudly. The revision is
exposed as ``resolved_revision`` and in ``GET /health``.

The import of ``chatterbox`` is LAZY (inside ``load()``) so the API can
start, answer /health, and run its unit tests on a CPU-only machine with
no GPU and no torch installed. GPU inference was NOT tested in this
environment — see docs/BUILD-LOG.md.

Watermark (m8): PerTh is applied inside Chatterbox ``generate()``
according to the wheel inspection, but that has NOT been verified on a
real GPU output. Until the §9.1 watermark-survival test passes on a
GPU, results report ``watermark="perth-unverified"`` — the header
asserts nothing unmeasured.

Urdu: there is deliberately no engine class here. ``mubashir-ur`` resolves
to ``EngineUnavailable`` until the gated spike (docs/URDU-SPIKE.md)
passes and an engine is wired in. Never fall back to English.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .audio import SAMPLE_RATE, float_samples_to_pcm16
from .config import SETTINGS
from .logging_config import logger
from .voices import ENGLISH_VOICE_IDS, URDU_VOICE_ID

REPO_ID = "ResembleAI/chatterbox-turbo"


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
    # "perth-unverified" until the watermark-survival test passes on a
    # real GPU output (m8). Never claim "perth-preserved" unmeasured.
    watermark: str = "perth-unverified"
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
    # Full commit SHA of the weights actually loaded, or None if the
    # engine has not loaded. Must equal ``revision`` when loaded (M3).
    resolved_revision: str | None = None

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

    def _download_checkpoint(self) -> Path:
        """Download the pinned revision. Fails loudly on any mismatch."""
        from huggingface_hub import snapshot_download  # lazy, GPU-only dep

        return Path(snapshot_download(repo_id=REPO_ID, revision=self.revision))

    def _load_turbo(self, ckpt_dir: Path) -> Any:
        from chatterbox.tts_turbo import ChatterboxTurboTTS  # lazy, GPU-only

        return ChatterboxTurboTTS.from_local(str(ckpt_dir), device=self.device)

    def load_english(self) -> None:
        """Load Chatterbox Turbo once, at the pinned revision. Safe to call repeatedly."""
        if self._loaded:
            return
        try:
            ckpt_dir = self._download_checkpoint()
            # snapshot_download returns .../snapshots/<commit-sha>/ — the
            # directory name IS the resolved commit. Enforce the pin.
            if ckpt_dir.name != self.revision:
                raise RuntimeError(
                    f"Chatterbox revision mismatch: expected {self.revision}, "
                    f"downloaded {ckpt_dir.name}"
                )
            self._turbo = self._load_turbo(ckpt_dir)
            self.resolved_revision = ckpt_dir.name
            self._loaded = True
        except Exception as exc:  # noqa: BLE001 — record, do not crash startup
            # Log the full error server-side; clients get only a generic
            # message (m9) — never leak paths / repo / network details.
            logger.error(
                "engine load failed",
                extra={"fields": {"error": f"{type(exc).__name__}: {exc}"}},
            )
            self._load_error = f"{type(exc).__name__}: {exc}"
            self._loaded = False
            self.resolved_revision = None

    def warmup(self) -> None:
        """Optional startup warmup (m7): load the model, and — if enabled
        and a reference clip exists — run one short generation so the
        first real request does not pay the cold-start cost."""
        self.load_english()
        if not SETTINGS.warmup_generate or not self._loaded or self._turbo is None:
            return
        for voice_id in ENGLISH_VOICE_IDS:
            if self.has_reference(voice_id):
                try:
                    ref_path = str(self.reference_path(voice_id))
                    self._turbo.generate("Hello.", audio_prompt_path=ref_path)
                except Exception as exc:  # noqa: BLE001 — warmup must never crash startup
                    logger.error(
                        "engine warmup generate failed",
                        extra={"fields": {"error": f"{type(exc).__name__}: {exc}"}},
                    )
                return

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
            # Generic message only — the detailed error is in the logs (m9).
            raise EngineUnavailable(
                voice_id,
                "Chatterbox Turbo failed to load. Check the server logs.",
            )
        started = time.monotonic()
        pcm_parts: list[bytes] = []
        turbo = self._turbo
        ref = str(self.reference_path(voice_id))
        for chunk in chunks:
            wav = turbo.generate(chunk, audio_prompt_path=ref)
            arr = wav.squeeze(0).detach().cpu().numpy()
            # Clip before casting (m11): a raw (arr * 32767).astype(int16)
            # wraps on samples > ±1.0 and produces clicks.
            pcm_parts.append(float_samples_to_pcm16(arr.tolist()))
        latency_ms = (time.monotonic() - started) * 1000.0
        return SynthesisResult(
            pcm16=b"".join(pcm_parts),
            sample_rate=SAMPLE_RATE,
            latency_ms=latency_ms,
            watermark="perth-unverified",
            chunks=len(chunks),
        )


REGISTRY = EngineRegistry()
