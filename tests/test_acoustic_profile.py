"""Acoustic profile + too-clean flag tests (gaps D1/D5).

No librosa, no Parselmouth, no torch in the test env: the pure
functions and the numpy autocorrelation F0 tracker are tested
directly. A test must never produce a fake acoustic number — the
"no library installed" path is tested to FAIL LOUDLY instead.
"""

import sys
import wave

import numpy as np
import pytest

import scripts.benchmark.acoustic_profile as ap

SR = 16000


def _write_wav(path, samples: np.ndarray, rate: int = SR) -> None:
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm.tobytes())


def _tone(seconds: float = 2.0, f0: float = 220.0, amp: float = 0.5) -> np.ndarray:
    t = np.arange(int(SR * seconds)) / SR
    return (np.sin(2 * np.pi * f0 * t) * amp).astype(np.float32)


def _human_like_tone(seconds: float = 2.0, seed: int = 0) -> np.ndarray:
    """Synthetic 'human-like' voiced signal: F0 wobble + amplitude
    modulation + low-level noise, so jitter/shimmer/HNR are all
    measurably above a pure tone's. NOT a human voice — only a
    test signal with nonzero micro-variation."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(SR * seconds)) / SR
    # F0: smooth 3 Hz wobble +-4 Hz PLUS genuine per-~30 ms random
    # variation (std ~2.5 Hz) — real frame-to-frame jitter, which a
    # smooth wobble alone does not produce at a 10 ms hop.
    n_knots = int(seconds * 30) + 2
    knots = 120.0 + rng.normal(0, 2.5, size=n_knots)
    knot_t = np.linspace(0, seconds, n_knots)
    f0_track = np.interp(t, knot_t, knots) + 4.0 * np.sin(2 * np.pi * 3 * t)
    phase = 2 * np.pi * np.cumsum(f0_track) / SR
    sig = np.sin(phase) * (1.0 + 0.08 * np.sin(2 * np.pi * 4 * t))
    sig = sig + rng.normal(0, 0.02, size=len(t))  # ~-28 dB noise
    return (sig * 0.5).astype(np.float32)


def _tone_wav(tmp_path, name: str, samples: np.ndarray):
    path = tmp_path / name
    _write_wav(path, samples)
    return path


# ---------------------------------------------------------------- loading


def test_load_wav_roundtrip_float32(tmp_path) -> None:
    path = _tone_wav(tmp_path, "tone.wav", _tone())
    samples, rate = ap.load_wav(path)
    assert samples.dtype == np.float32  # float32 in, float32 out
    assert rate == SR
    assert len(samples) == SR * 2
    assert float(np.max(np.abs(samples))) == pytest.approx(0.5, abs=0.01)


def test_load_wav_missing_file_raises(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        ap.load_wav(tmp_path / "nope.wav")


def test_load_wav_stereo_downmixed(tmp_path) -> None:
    path = tmp_path / "stereo.wav"
    pcm16 = (np.clip(_tone(), -1, 1) * 32767).astype(np.int16)
    stereo = np.column_stack([pcm16, pcm16])
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(stereo.tobytes())
    samples, _ = ap.load_wav(path)
    assert samples.dtype == np.float32
    assert len(samples) == SR * 2


# ---------------------------------------------------------------- F0 (known tones)


def test_f0_known_tone_220hz(tmp_path) -> None:
    path = _tone_wav(tmp_path, "tone220.wav", _tone(f0=220.0))
    profile = ap.profile_wav(path, f0_method="autocorr")
    assert profile["f0_method"] == "autocorrelation"
    assert profile["f0"]["mean_hz"] == pytest.approx(220.0, abs=5.0)


def test_f0_known_tone_110hz(tmp_path) -> None:
    path = _tone_wav(tmp_path, "tone110.wav", _tone(f0=110.0))
    profile = ap.profile_wav(path, f0_method="autocorr")
    assert profile["f0"]["mean_hz"] == pytest.approx(110.0, abs=5.0)


def test_f0_wobbled_tone_has_semitone_sd(tmp_path) -> None:
    path = _tone_wav(tmp_path, "wobble.wav", _human_like_tone())
    profile = ap.profile_wav(path, f0_method="autocorr")
    assert profile["f0"]["sd_semitones"] is not None
    assert profile["f0"]["sd_semitones"] > 0.1


# ---------------------------------------------------------------- silence


def test_silence_profiles_without_fake_numbers(tmp_path) -> None:
    """Silence: F0 measures are null (never 0), pause % is 100."""
    path = _tone_wav(tmp_path, "silence.wav", np.zeros(SR * 2, dtype=np.float32))
    profile = ap.profile_wav(path, f0_method="autocorr")
    assert profile["f0"]["mean_hz"] is None
    assert profile["f0"]["sd_semitones"] is None
    assert profile["jitter_local_pct"] is None
    assert profile["shimmer_local_pct"] is None
    assert profile["hnr_db"] is None
    assert profile["h1_h2_db"] is None
    assert profile["pauses"]["pause_pct"] == pytest.approx(100.0)
    assert profile["pauses"]["breath_pct"] == pytest.approx(0.0)
    assert profile["speaking_rate"]["syllables_est"] == 0


def test_very_short_file_does_not_crash(tmp_path) -> None:
    path = _tone_wav(tmp_path, "short.wav", _tone(seconds=0.05))
    profile = ap.profile_wav(path, f0_method="autocorr")
    assert profile["duration_s"] == pytest.approx(0.05, abs=0.01)


# ---------------------------------------------------------------- pauses / rate


def test_pause_detected_in_middle_gap(tmp_path) -> None:
    sig = np.concatenate([_tone(seconds=1.0), np.zeros(SR // 2), _tone(seconds=1.0)])
    path = _tone_wav(tmp_path, "gap.wav", sig)
    profile = ap.profile_wav(path, f0_method="autocorr")
    assert profile["pauses"]["count"] >= 1
    assert profile["pauses"]["total_s"] == pytest.approx(0.5, abs=0.1)
    assert 10.0 < profile["pauses"]["pause_pct"] < 30.0


def test_syllable_estimator_counts_am_bursts(tmp_path) -> None:
    """4 Hz amplitude modulation over 2 s -> ~8 envelope peaks."""
    t = np.arange(SR * 2) / SR
    sig = (np.sin(2 * np.pi * 120 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 4 * t))).astype(np.float32)
    path = _tone_wav(tmp_path, "am.wav", sig)
    profile = ap.profile_wav(path, f0_method="autocorr")
    assert profile["speaking_rate"]["syllables_est"] >= 4


def test_h1_h2_pure_tone_is_large(tmp_path) -> None:
    """A pure sine has almost no 2nd harmonic: H1-H2 must be large positive."""
    path = _tone_wav(tmp_path, "tone.wav", _tone())
    profile = ap.profile_wav(path, f0_method="autocorr")
    assert profile["h1_h2_db"] is not None
    assert profile["h1_h2_db"] > 10.0


# ---------------------------------------------------------------- compare mode


def test_compare_too_clean_pure_tone_flagged(tmp_path) -> None:
    """Pure steady tone as 'clone' vs noisy/wobbled tone as 'reference':
    jitter ~0, shimmer ~0, HNR capped high -> too_clean must fire."""
    ref = _tone_wav(tmp_path, "ref.wav", _human_like_tone(seed=1))
    clone = _tone_wav(tmp_path, "clone.wav", _tone(f0=120.0))
    result = ap.compare_profiles(ref, clone, f0_method="autocorr")
    assert result["flags"]["too_clean"] is True
    assert (
        result["flags"]["jitter_too_clean"]
        or result["flags"]["shimmer_too_clean"]
        or result["flags"]["hnr_too_clean"]
    )
    assert result["deltas_clone_minus_reference"]["hnr_db"] is not None
    assert result["deltas_clone_minus_reference"]["hnr_db"] > 0


def test_compare_matched_tones_not_flagged(tmp_path) -> None:
    """Same construction, different seed: micro-variation matches, no flag."""
    ref = _tone_wav(tmp_path, "ref.wav", _human_like_tone(seed=2))
    clone = _tone_wav(tmp_path, "clone.wav", _human_like_tone(seed=3))
    result = ap.compare_profiles(ref, clone, f0_method="autocorr")
    assert result["flags"]["too_clean"] is False
    assert result["flags"]["jitter_too_clean"] is False
    assert result["flags"]["shimmer_too_clean"] is False
    assert result["flags"]["hnr_too_clean"] is False


def test_compare_deltas_sign(tmp_path) -> None:
    ref = _tone_wav(tmp_path, "ref.wav", _tone(f0=120.0))
    clone = _tone_wav(tmp_path, "clone.wav", _tone(f0=180.0))
    result = ap.compare_profiles(ref, clone, f0_method="autocorr")
    assert result["deltas_clone_minus_reference"]["f0_mean_hz"] == pytest.approx(60.0, abs=8.0)


# ---------------------------------------------------------------- loud failure


def test_pyin_method_without_librosa_fails_loudly(tmp_path, monkeypatch) -> None:
    """librosa is not installed in the test env; requesting pyin must
    raise a clear RuntimeError naming librosa — never silently fall
    back and report numbers from another method."""
    monkeypatch.setitem(sys.modules, "librosa", None)
    path = _tone_wav(tmp_path, "tone.wav", _tone())
    with pytest.raises(RuntimeError, match="librosa is not installed"):
        ap.profile_wav(path, f0_method="pyin")


def test_cli_missing_files_exits_2(capsys) -> None:
    assert ap.main(["--wav", "/nope/missing.wav"]) == 2
    assert "error:" in capsys.readouterr().err
    assert ap.main(["--ref", "/nope/ref.wav", "--clone", "/nope/clone.wav"]) == 2
    assert "error:" in capsys.readouterr().err


def test_cli_missing_librosa_exits_2(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setitem(sys.modules, "librosa", None)
    path = _tone_wav(tmp_path, "tone.wav", _tone())
    assert ap.main(["--wav", str(path), "--f0-method", "pyin"]) == 2
    assert "librosa" in capsys.readouterr().err


def test_cli_bad_args_exits_2(capsys) -> None:
    assert ap.main([]) == 2
    assert "error:" in capsys.readouterr().err


def test_cli_single_wav_exits_0(tmp_path, capsys) -> None:
    path = _tone_wav(tmp_path, "tone.wav", _tone())
    assert ap.main(["--wav", str(path), "--f0-method", "autocorr"]) == 0
    assert "mean_hz" in capsys.readouterr().out
