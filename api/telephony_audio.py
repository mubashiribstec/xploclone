"""Phone-line audio: 8 kHz resampling and G.711 μ-law, in numpy.

Ported from VoiceStudio (debpalash/VoiceStudio,
``backend/services/telephony/audio.py``, AGPL-3.0-only) into XploClone,
a private personal-learning repo, as the telephony core (Phase 1 of
the VoiceStudio port). The codec itself is a vectorised port of the
reference Sun ``g711.c`` that ``audioop`` itself used — bit-identical
to ``audioop.lin2ulaw`` / ``ulaw2lin`` (pinned in
``tests/test_telephony_audio.py`` while a Python with ``audioop`` is
available; ``audioop`` was removed in Python 3.13 and XploClone
targets Python 3.14, so the CPython golden-vector tests are the
permanent pin).

Audit fixes vs the VoiceStudio original (full list in
``docs/TELEPHONY-PORT-PHASE1.md``):
- ``ulaw_to_wav`` uses the stdlib ``wave`` module instead of
  ``soundfile`` (XploClone's ``api/audio.py`` already does this).
- ``lin2ulaw`` validates its input: float input is rejected with
  ``TypeError`` (convert with ``float_to_pcm16`` first); integer
  input outside the int16 range is clipped instead of silently
  wrapping on overflow.
- ``resample_to_phone`` sanitises non-finite samples before
  resampling, so NaN/inf can no longer propagate into phone audio.
- ``resample_to_phone`` imports torch only when resampling is
  actually needed: the 8 kHz passthrough and the bad-rate check run
  without torch, so CPU-only tests and callers that never resample
  do not need the dependency installed at all.
- New helper ``pcm16_to_ulaw`` (PCM16 bytes in, μ-law bytes out) for
  the streaming path, so the WebSocket handler never handles raw
  torch tensors.
"""

from __future__ import annotations

import io
import wave
from typing import Any

import numpy as np

PHONE_SAMPLE_RATE = 8000
#: One 20 ms frame of 8 kHz μ-law = 160 bytes (one byte per sample).
FRAME_MS = 20
FRAME_BYTES = PHONE_SAMPLE_RATE * FRAME_MS // 1000
#: μ-law byte for digital silence.
ULAW_SILENCE = 0xFF

_BIAS = 0x21  # 33, applied to the 14-bit magnitude (Sun g711.c)
_CLIP = 8159
_SEG_END = np.array([0x3F, 0x7F, 0xFF, 0x1FF, 0x3FF, 0x7FF, 0xFFF, 0x1FFF], dtype=np.int32)


def float_to_pcm16(samples: Any) -> np.ndarray:
    """[-1, 1] floats (any shape; first channel kept) → int16 mono."""
    arr = np.asarray(samples, dtype=np.float32)
    if arr.ndim == 2:
        arr = arr[0]
    arr = np.nan_to_num(arr.reshape(-1), nan=0.0, posinf=1.0, neginf=-1.0)
    return np.clip(np.round(arr * 32767.0), -32768, 32767).astype(np.int16)


def lin2ulaw(pcm16: Any) -> bytes:
    """int16 PCM → G.711 μ-law bytes (identical to ``audioop.lin2ulaw(x, 2)``).

    Integer input of any width is accepted and clipped to the int16
    range; float input is rejected — convert it with
    :func:`float_to_pcm16` first. The VoiceStudio original cast
    blindly to int16, which silently wraps out-of-range values (and
    truncates floats) into wrong μ-law bytes.
    """
    arr = np.asarray(pcm16)
    if arr.dtype.kind in ("f", "c"):
        raise TypeError(
            "lin2ulaw takes integer PCM; convert floats with float_to_pcm16 first"
        )
    if arr.dtype.kind not in ("i", "u", "b"):
        raise TypeError(f"lin2ulaw takes integer PCM, got dtype {arr.dtype}")
    pcm = np.clip(arr.astype(np.int64), -32768, 32767).astype(np.int32) >> 2  # 14-bit
    negative = pcm < 0
    mag = np.where(negative, -pcm, pcm)
    mag = np.minimum(mag, _CLIP) + _BIAS
    mask = np.where(negative, 0x7F, 0xFF)
    seg = np.searchsorted(_SEG_END, mag, side="left")
    shifted = mag >> np.minimum(seg + 1, 31)
    uval = np.where(seg >= 8, 0x7F, (seg << 4) | (shifted & 0xF))
    return (uval ^ mask).astype(np.uint8).tobytes()


def ulaw2lin(data: bytes) -> np.ndarray:
    """G.711 μ-law bytes → int16 PCM (identical to ``audioop.ulaw2lin(x, 2)``)."""
    u = (~np.frombuffer(data, dtype=np.uint8)).astype(np.int32) & 0xFF
    t = ((u & 0x0F) << 3) + 0x84
    t = t << ((u & 0x70) >> 4)
    return np.where(u & 0x80, 0x84 - t, t - 0x84).astype(np.int16)


def resample_to_phone(samples: Any, sample_rate: int) -> np.ndarray:
    """Mono float audio at ``sample_rate`` → float32 at 8 kHz.

    torchaudio's windowed-sinc resampler low-passes before decimating, so
    content above the 4 kHz phone Nyquist is filtered rather than aliased
    into the band a caller hears. Non-finite samples are sanitised first
    (fix vs the VoiceStudio original, which let NaN/inf through).
    """
    arr = np.asarray(samples, dtype=np.float32)
    if arr.ndim == 2:
        arr = arr[0]
    arr = np.nan_to_num(arr.reshape(-1), nan=0.0, posinf=1.0, neginf=-1.0)
    if sample_rate == PHONE_SAMPLE_RATE or arr.size == 0:
        return arr.copy()
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    # torch is imported lazily AND only when resampling is actually
    # needed (fix vs the port's first draft, which imported torch
    # before the 8 kHz passthrough above — so even a no-op call needed
    # torch installed). Tests run without torch.
    import torch
    import torchaudio

    out = torchaudio.functional.resample(
        torch.from_numpy(np.ascontiguousarray(arr)), int(sample_rate), PHONE_SAMPLE_RATE
    )
    return out.numpy().astype(np.float32, copy=False)


def to_phone_ulaw(samples: Any, sample_rate: int) -> bytes:
    """Any-rate float audio → 8 kHz mono μ-law bytes."""
    if hasattr(samples, "detach"):
        samples = samples.detach().cpu().float().numpy()
    return lin2ulaw(float_to_pcm16(resample_to_phone(samples, sample_rate)))


def pcm16_to_ulaw(pcm16: bytes, sample_rate: int) -> bytes:
    """PCM16 bytes at ``sample_rate`` → 8 kHz mono μ-law bytes.

    The streaming path's converter: the engine yields PCM16 bytes, this
    turns them into phone-line bytes without touching torch tensors.
    """
    if len(pcm16) % 2 != 0:
        raise ValueError("PCM16 data must have an even byte length")
    floats = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32768.0
    return lin2ulaw(float_to_pcm16(resample_to_phone(floats, sample_rate)))


def iter_frames(ulaw: bytes, frame_bytes: int = FRAME_BYTES) -> Any:
    """Split μ-law audio into fixed 20 ms frames; the tail is silence-padded
    so every frame the line receives is exactly ``frame_bytes`` long."""
    for start in range(0, len(ulaw), frame_bytes):
        frame = ulaw[start:start + frame_bytes]
        if len(frame) < frame_bytes:
            frame = frame + bytes([ULAW_SILENCE]) * (frame_bytes - len(frame))
        yield frame


def ulaw_to_wav(ulaw: bytes) -> bytes:
    """Decode μ-law to a PCM16 8 kHz WAV any browser can play.

    Used by the local preview: the audio goes through the exact encode →
    decode round trip a phone call applies, so the user hears line quality.
    (Browsers do not reliably play μ-law WAVs, hence decoding here.)

    Uses the stdlib ``wave`` module (as ``api/audio.py`` does) instead of
    the ``soundfile`` dependency the VoiceStudio original required.
    """
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(PHONE_SAMPLE_RATE)
        wav.writeframes(ulaw2lin(ulaw).tobytes())
    return buf.getvalue()
