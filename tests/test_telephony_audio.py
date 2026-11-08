"""Tests for the telephony μ-law codec (api/telephony_audio.py).

The codec is a port of the reference Sun g711.c that ``audioop``
itself used, so the primary pin is bit-identity against ``audioop``.
``audioop`` was removed in Python 3.13 and XploClone targets Python
3.14, so the CPython golden-vector tests are the permanent pin that
survives after ``audioop`` is gone: if the audioop tests are skipped,
the golden vectors must still pass.
"""

from __future__ import annotations

import io
import wave

import numpy as np
import pytest

from api.telephony_audio import (
    FRAME_BYTES,
    PHONE_SAMPLE_RATE,
    ULAW_SILENCE,
    float_to_pcm16,
    iter_frames,
    lin2ulaw,
    pcm16_to_ulaw,
    resample_to_phone,
    ulaw2lin,
    ulaw_to_wav,
)

audioop = None
try:
    import audioop as _audioop

    audioop = _audioop
except ImportError:  # Python 3.13+: audioop is gone; golden vectors pin the codec.
    audioop = None

needs_audioop = pytest.mark.skipif(audioop is None, reason="audioop removed in Python 3.13+")

# VoiceStudio's own test vectors (backend/services/telephony/audio.py):
# lin2ulaw([0, 0x1234, 0x4567, -0x4567, 0x7FFF, -0x8000, -1]).
GOLDEN_PCM = [0, 0x1234, 0x4567, -0x4567, 0x7FFF, -0x8000, -1]
GOLDEN_ULAW = bytes.fromhex("ffad8e0e80007e")
# ulaw2lin([0xFF, 0x7F, 0x80, 0x00, 0xF0, 0x70]).
GOLDEN_ULAW_IN = bytes([0xFF, 0x7F, 0x80, 0x00, 0xF0, 0x70])
GOLDEN_PCM_OUT = [0, 0, 32124, -32124, 120, -120]


@needs_audioop
def test_lin2ulaw_matches_audioop_random():
    rng = np.random.default_rng(20261105)
    for size in (0, 1, 2, 100, 4096):
        pcm = rng.integers(-32768, 32768, size=size, dtype=np.int16)
        assert lin2ulaw(pcm) == audioop.lin2ulaw(pcm.tobytes(), 2)


@needs_audioop
def test_lin2ulaw_matches_audioop_edges():
    pcm = np.array(
        [-32768, -32767, -8192, -4096, -1, 0, 1, 4095, 8191, 32766, 32767],
        dtype=np.int16,
    )
    assert lin2ulaw(pcm) == audioop.lin2ulaw(pcm.tobytes(), 2)


@needs_audioop
def test_ulaw2lin_matches_audioop_all_codes():
    data = bytes(range(256))
    assert ulaw2lin(data).tobytes() == audioop.ulaw2lin(data, 2)


def test_golden_vectors():
    assert lin2ulaw(np.array(GOLDEN_PCM, dtype=np.int16)) == GOLDEN_ULAW
    assert ulaw2lin(GOLDEN_ULAW_IN).tolist() == GOLDEN_PCM_OUT


def test_roundtrip_codeword_identity():
    """Every μ-law code decodes to a PCM value that re-encodes to itself
    — except 0x7F, which shares PCM 0 with 0xFF (μ-law has two zeros;
    the encoder canonically picks 0xFF). audioop behaves identically."""
    for code in range(256):
        if code == 0x7F:
            continue
        pcm = ulaw2lin(bytes([code]))
        assert lin2ulaw(pcm) == bytes([code])
    assert ulaw2lin(bytes([0x7F]))[0] == 0
    assert lin2ulaw(np.array([0], dtype=np.int16)) == bytes([0xFF])


def test_lin2ulaw_rejects_floats():
    with pytest.raises(TypeError):
        lin2ulaw(np.array([0.0, 0.5, -0.5], dtype=np.float32))
    with pytest.raises(TypeError):
        lin2ulaw([0.0, 1.0])


def test_lin2ulaw_clips_out_of_range_ints():
    """Port fix: the VoiceStudio original cast blindly to int16, which
    silently wrapped out-of-range values into wrong μ-law bytes."""
    clipped = lin2ulaw(np.array([40000, -40000, 32767, -32768], dtype=np.int32))
    expected = lin2ulaw(np.array([32767, -32768, 32767, -32768], dtype=np.int16))
    assert clipped == expected


def test_ulaw_silence_is_silence():
    assert ulaw2lin(bytes([ULAW_SILENCE]))[0] == 0
    assert lin2ulaw(np.array([0], dtype=np.int16)) == bytes([ULAW_SILENCE])


def test_float_to_pcm16_sanitises_non_finite():
    out = float_to_pcm16([float("nan"), float("inf"), float("-inf"), 0.5, -1.0, 1.0])
    assert out.tolist() == [0, 32767, -32767, 16384, -32767, 32767]


def test_resample_to_phone_passthrough_at_8k():
    """At 8 kHz no resampling (and no torch) is needed; NaN/inf are
    still sanitised first."""
    samples = np.array([0.0, 0.5, float("nan"), float("inf"), -1.0], dtype=np.float32)
    out = resample_to_phone(samples, PHONE_SAMPLE_RATE)
    assert out.dtype == np.float32
    assert out.tolist() == [0.0, 0.5, 0.0, 1.0, -1.0]


def test_resample_to_phone_rejects_bad_rate():
    with pytest.raises(ValueError):
        resample_to_phone(np.array([0.1, 0.2], dtype=np.float32), 0)


def test_pcm16_to_ulaw_rejects_odd_length():
    with pytest.raises(ValueError):
        pcm16_to_ulaw(b"\x00\x00\x00", PHONE_SAMPLE_RATE)


def test_pcm16_to_ulaw_silence_at_8k():
    silence = np.zeros(800, dtype=np.int16).tobytes()
    assert pcm16_to_ulaw(silence, PHONE_SAMPLE_RATE) == bytes([ULAW_SILENCE]) * 800


def test_iter_frames_pads_tail_with_silence():
    frames = list(iter_frames(bytes(100)))
    assert len(frames) == 1
    assert len(frames[0]) == FRAME_BYTES
    assert frames[0][:100] == bytes(100)
    assert frames[0][100:] == bytes([ULAW_SILENCE]) * (FRAME_BYTES - 100)


def test_ulaw_to_wav_roundtrip():
    ulaw = bytes([ULAW_SILENCE]) * 160 + lin2ulaw(np.array([1000, -1000] * 80, dtype=np.int16))
    wav_bytes = ulaw_to_wav(ulaw)
    with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == PHONE_SAMPLE_RATE
        assert wav.getnframes() == len(ulaw)
        frames = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16)
    assert frames[:160].tolist() == [0] * 160
    assert frames[160:].tolist() == ulaw2lin(ulaw[160:]).tolist()
