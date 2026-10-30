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

Nano (CPU test mode, verified 2026-10-30 from the HF model card
ResembleAI/chatterbox-nano): the same class, ``from_pretrained(device,
nano=True)``, 10 s reference clip, vendor claim 3x real-time on CPU
with 8 threads — unmeasured here. ``from_local`` may not accept
``nano=`` in 0.1.7, so the loader tries it and falls back.

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
from collections.abc import Generator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .audio import SAMPLE_RATE, float_samples_to_pcm16
from .config import SETTINGS
from .logging_config import logger
from .voices import ENGLISH_VOICE_IDS, URDU_VOICE_ID

REPO_ID = "ResembleAI/chatterbox-turbo"
REPO_ID_NANO = "ResembleAI/chatterbox-nano"


def _set_torch_threads() -> None:
    """On CPU, cap torch threads to the configured value (0 = default).

    Called lazily at first engine load, never at import time, so unit
    tests without torch are unaffected. Guarded: if torch is missing
    or refuses, log and continue with torch's default.
    """
    if SETTINGS.device != "cpu" or SETTINGS.torch_threads <= 0:
        return
    try:
        import torch

        torch.set_num_threads(SETTINGS.torch_threads)
        logger.info(
            "torch threads set",
            extra={"fields": {"threads": SETTINGS.torch_threads}},
        )
    except Exception as exc:  # noqa: BLE001 — threads are a hint, not a gate
        logger.error(
            "torch thread config failed",
            extra={"fields": {"error": f"{type(exc).__name__}: {exc}"}},
        )


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
    # "turbo" (350M, GPU prod) or "nano" (110M, CPU test mode).
    # Nano uses the same ChatterboxTurboTTS class with nano=True
    # (HF ResembleAI/chatterbox-nano, MIT). Unknown values fall back
    # to turbo loudly at load time — never silently.
    engine_name: str = SETTINGS.engine
    nano_revision: str = SETTINGS.chatterbox_nano_revision
    _turbo: Any = None
    _loaded: bool = False
    _load_error: str | None = None
    # Full commit SHA of the weights actually loaded, or None if the
    # engine has not loaded. Must equal ``revision`` when loaded (M3).
    resolved_revision: str | None = None
    # Reference-clip stat cache: (voice_id -> (mtime_ns, size)). The
    # reference audio is re-encoded by generate() on every chunk (the
    # 0.1.7 API takes audio_prompt_path per call and exposes no
    # embedding object to cache), so this only avoids repeated
    # stat() calls in has_reference(); it does NOT claim the
    # embedding is cached. Identical-request audio caching lives in
    # api/cache.py instead.
    _ref_stat_cache: dict[str, tuple[int, int]] = field(default_factory=dict)

    @property
    def _is_nano(self) -> bool:
        return self.engine_name == "nano"

    @property
    def _repo_id(self) -> str:
        return REPO_ID_NANO if self._is_nano else REPO_ID

    @property
    def _pinned_revision(self) -> str:
        # Nano: empty pin means "record the resolved commit, pin it
        # before Gate 1" — see config.py. Turbo: always pinned.
        return self.nano_revision if self._is_nano else self.revision

    def reference_path(self, voice_id: str) -> Path:
        return self.ref_dir / f"{voice_id}.wav"

    def has_reference(self, voice_id: str) -> bool:
        path = self.reference_path(voice_id)
        try:
            stat = path.stat()
        except OSError:
            self._ref_stat_cache.pop(voice_id, None)
            return False
        if stat.st_size <= 0:
            return False
        cached = self._ref_stat_cache.get(voice_id)
        if cached is not None and cached == (stat.st_mtime_ns, stat.st_size):
            return True
        self._ref_stat_cache[voice_id] = (stat.st_mtime_ns, stat.st_size)
        return path.is_file()

    def status(self, voice_id: str) -> str:
        """'loaded' | 'unavailable' — as reported by GET /v1/voices."""
        if voice_id == URDU_VOICE_ID:
            return "unavailable"
        if voice_id in ENGLISH_VOICE_IDS:
            return "loaded" if (self._loaded and self.has_reference(voice_id)) else "unavailable"
        return "unavailable"

    def _download_checkpoint(self) -> Path:
        """Download the pinned revision. Fails loudly on any mismatch.

        Turbo: revision is always pinned (M3). Nano: an empty pin
        downloads the repo default and the resolved commit is
        recorded — the operator must pin it before Gate 1.
        """
        from huggingface_hub import snapshot_download  # lazy, GPU-only dep

        revision = self._pinned_revision or None
        return Path(snapshot_download(repo_id=self._repo_id, revision=revision))

    def _load_turbo(self, ckpt_dir: Path) -> Any:
        from chatterbox.tts_turbo import ChatterboxTurboTTS  # lazy, GPU-only

        if not self._is_nano:
            return ChatterboxTurboTTS.from_local(str(ckpt_dir), device=self.device)
        # Nano shares the Turbo class (HF model card, verified
        # 2026-10-30): from_pretrained(device, nano=True). from_local
        # may not accept nano= in this version, so try it and fall
        # back to the plain call — and record which path was used.
        try:
            return ChatterboxTurboTTS.from_local(str(ckpt_dir), device=self.device, nano=True)  # type: ignore[call-arg]
        except TypeError:
            logger.info(
                "nano from_local has no nano kwarg, using plain from_local",
                extra={"fields": {"engine": "nano"}},
            )
            return ChatterboxTurboTTS.from_local(str(ckpt_dir), device=self.device)

    def load_english(self) -> None:
        """Load the selected engine once, at the pinned revision. Safe to call repeatedly."""
        if self._loaded:
            return
        if self.engine_name not in ("turbo", "nano"):
            self._load_error = f"Unknown engine: {self.engine_name!r} (want turbo|nano)"
            logger.error("engine load failed", extra={"fields": {"error": self._load_error}})
            return
        _set_torch_threads()
        try:
            ckpt_dir = self._download_checkpoint()
            # snapshot_download returns .../snapshots/<commit-sha>/ — the
            # directory name IS the resolved commit. Enforce the pin.
            if self._pinned_revision and ckpt_dir.name != self._pinned_revision:
                raise RuntimeError(
                    f"Chatterbox revision mismatch: expected {self._pinned_revision}, "
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

    def ensure_loaded(self, voice_id: str) -> None:
        """Validate voice/reference and load the engine, or raise 503."""
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

    def _synthesise_one(self, voice_id: str, chunk: str) -> bytes:
        """Generate one chunk. Caller must have called _ensure_loaded."""
        assert self._turbo is not None  # guaranteed by _ensure_loaded
        ref = str(self.reference_path(voice_id))
        wav = self._turbo.generate(chunk, audio_prompt_path=ref)
        arr = wav.squeeze(0).detach().cpu().numpy()
        # Clip before casting (m11): a raw (arr * 32767).astype(int16)
        # wraps on samples > ±1.0 and produces clicks.
        return float_samples_to_pcm16(arr.tolist())

    def synthesize_one(self, voice_id: str, chunk: str) -> bytes:
        """Generate one chunk (public, for per-sentence HTTP streaming).

        Caller must have called ensure_loaded() first.
        """
        return self._synthesise_one(voice_id, chunk)

    def synthesize_stream(self, voice_id: str, chunks: list[str]) -> Generator[bytes]:
        """Yield PCM16 bytes per chunk, in order.

        A generator (not a list): the HTTP layer can send the first
        chunk before the last one is synthesised. Each chunk is still
        generated synchronously by the caller (via to_thread, one
        chunk at a time) — this does not make the model faster, it
        only removes the wait-for-everything before the first byte.
        """
        self.ensure_loaded(voice_id)
        for chunk in chunks:
            yield self._synthesise_one(voice_id, chunk)

    def synthesize(self, voice_id: str, chunks: list[str]) -> SynthesisResult:
        """Synthesise chunked text in one voice. Returns concatenated PCM16."""
        self.ensure_loaded(voice_id)
        started = time.monotonic()
        pcm_parts = list(self.synthesize_stream(voice_id, chunks))
        latency_ms = (time.monotonic() - started) * 1000.0
        return SynthesisResult(
            pcm16=b"".join(pcm_parts),
            sample_rate=SAMPLE_RATE,
            latency_ms=latency_ms,
            watermark="perth-unverified",
            chunks=len(chunks),
        )


REGISTRY = EngineRegistry()
