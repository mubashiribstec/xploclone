"""Audio helpers — WAV encoding only (no model code here).

Output format for v1 file generation is 24 kHz, 16-bit, mono WAV
(``S3GEN_SR`` of Chatterbox Turbo, verified from chatterbox-tts 0.1.7).
MP3 is NOT supported in v1: it needs ffmpeg at request time and adds a
transcoding failure mode the MVP does not need. If MP3 is required later,
add it behind an explicit flag and a test — do not silently shell out.
"""

from __future__ import annotations

import io
import struct
import wave

SAMPLE_RATE = 24000


def pcm16_to_wav(pcm: bytes, sample_rate: int = SAMPLE_RATE) -> bytes:
    """Wrap raw little-endian PCM16 mono bytes in a WAV container."""
    if len(pcm) % 2 != 0:
        raise ValueError("PCM16 data must have an even byte length")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)
    return buf.getvalue()


def float_samples_to_pcm16(samples: list[float]) -> bytes:
    """Convert float samples in [-1.0, 1.0] to PCM16 bytes (clipped)."""
    clamped = [max(-1.0, min(1.0, float(s))) for s in samples]
    return struct.pack(f"<{len(clamped)}h", *[int(s * 32767) for s in clamped])


def sine_pcm16(duration_s: float, freq_hz: float = 440.0, sample_rate: int = SAMPLE_RATE) -> bytes:
    """Test-only tone generator (no GPU, no model). Used by unit tests."""
    import math

    n = int(duration_s * sample_rate)
    samples = [0.3 * math.sin(2.0 * math.pi * freq_hz * i / sample_rate) for i in range(n)]
    return float_samples_to_pcm16(samples)
