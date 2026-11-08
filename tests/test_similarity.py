"""SIM + long-form drift tests (gaps A1/A2).

No model download, no torch, no SpeechBrain: the pure functions
(cosine, drift, WAV loading) are tested directly, and the embedding
step is tested with a stubbed ``embed_wav``. A test must never
produce a fake SIM score — the "no model installed" path is tested
to FAIL LOUDLY instead.
"""

import math
import wave

import numpy as np
import pytest

import scripts.benchmark.similarity as sim


def test_cosine_identical_is_one() -> None:
    a = np.array([1.0, 2.0, 3.0])
    assert sim.cosine_similarity(a, a) == pytest.approx(1.0)


def test_cosine_orthogonal_is_zero() -> None:
    assert sim.cosine_similarity(np.array([1.0, 0.0]), np.array([0.0, 1.0])) == pytest.approx(0.0)


def test_cosine_opposite_is_minus_one() -> None:
    assert sim.cosine_similarity(np.array([1.0, 0.0]), np.array([-1.0, 0.0])) == pytest.approx(-1.0)


def test_cosine_shape_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="shapes differ"):
        sim.cosine_similarity(np.array([1.0, 2.0]), np.array([1.0, 2.0, 3.0]))


def test_cosine_zero_vector_raises() -> None:
    with pytest.raises(ValueError, match="zero-norm"):
        sim.cosine_similarity(np.zeros(3), np.ones(3))


def test_drift_report_no_drift() -> None:
    report = sim.drift_report(0.85, 0.84)
    assert report["drift"] == pytest.approx(-0.01)
    assert report["drift_flagged"] is False


def test_drift_report_vendor_style_collapse_flagged() -> None:
    """The failure mode from the skill (SIM ~0.80 -> ~0.52 over
    minutes) must be flagged, not averaged away."""
    report = sim.drift_report(0.80, 0.52)
    assert report["drift"] == pytest.approx(-0.28)
    assert report["drift_flagged"] is True


def _write_wav(path, samples: np.ndarray, rate: int = 16000) -> None:
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm.tobytes())


def test_load_wav_mono_16k_roundtrip(tmp_path) -> None:
    path = tmp_path / "tone.wav"
    _write_wav(path, np.sin(np.linspace(0, 10, 16000)) * 0.5)
    loaded = sim.load_wav_mono_16k(path)
    assert loaded.dtype == np.float32
    assert len(loaded) == 16000
    assert float(np.max(np.abs(loaded))) == pytest.approx(0.5, abs=0.01)


def test_load_wav_missing_file_raises(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        sim.load_wav_mono_16k(tmp_path / "nope.wav")


def test_load_wav_wrong_rate_raises(tmp_path) -> None:
    """A non-16 kHz file is an error, not a silent resample."""
    path = tmp_path / "eight-k.wav"
    _write_wav(path, np.zeros(8000), rate=8000)
    with pytest.raises(ValueError, match="16000 Hz"):
        sim.load_wav_mono_16k(path)


def test_window_samples_needs_two_minutes(tmp_path) -> None:
    with pytest.raises(ValueError, match="at least 60"):
        sim.window_samples(np.zeros(16000 * 30), window_s=30.0)


def test_window_samples_first_and_last(tmp_path) -> None:
    samples = np.arange(16000 * 90, dtype=np.float32)
    first, last = sim.window_samples(samples, window_s=30.0)
    assert len(first) == len(last) == 16000 * 30
    assert first[0] == 0.0
    assert last[-1] == float(16000 * 90 - 1)


def test_unsupported_embedding_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported embedding"):
        sim.load_embedding_model("wavlm-tdnn")


def test_missing_speechbrain_fails_loudly_not_fake_score() -> None:
    """SpeechBrain is not installed in the test env. similarity()
    must raise a clear RuntimeError — never return a made-up number."""
    with pytest.raises(RuntimeError, match="SpeechBrain is not installed"):
        sim.load_embedding_model("ecapa-tdnn")


def test_cli_missing_files_exits_2(capsys) -> None:
    assert sim.main(["--ref", "/nope/ref.wav", "--gen", "/nope/gen.wav"]) == 2
    assert "error:" in capsys.readouterr().err


def _sine_wav(tmp_path, name: str, seconds: float = 1.0):  # type: ignore[no-untyped-def]
    path = tmp_path / name
    t = np.linspace(0, 2 * math.pi * 440 * seconds, int(16000 * seconds), endpoint=False)
    _write_wav(path, np.sin(t) * 0.5)
    return path


def test_similarity_with_stubbed_embedding(tmp_path, monkeypatch) -> None:
    """Plumbing test: with a stub embedding that returns the same
    vector for both files, SIM is 1.0. The stub replaces embed_wav
    only — cosine and WAV loading are the real code."""
    ref = _sine_wav(tmp_path, "ref.wav")
    gen = _sine_wav(tmp_path, "gen.wav")
    monkeypatch.setattr(sim, "embed_wav", lambda model, samples: np.array([1.0, 0.0, 0.0]))
    result = sim.similarity(ref, gen, model=object())
    assert result["embedding"] == "ecapa-tdnn"
    assert result["similarity"] == pytest.approx(1.0)
    assert result["target"] == 0.80


def test_long_form_drift_with_stubbed_embedding(tmp_path, monkeypatch) -> None:
    """Stub returns: ref = [1,0], first window = [1,0] (SIM 1.0),
    last window = [0,1] (SIM 0.0) — drift -1.0, flagged."""
    ref = _sine_wav(tmp_path, "ref.wav", seconds=1.0)
    gen = _sine_wav(tmp_path, "gen.wav", seconds=90.0)
    calls = {"n": 0}

    def fake_embed(model, samples):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        if calls["n"] == 1:  # reference
            return np.array([1.0, 0.0])
        if calls["n"] == 2:  # first window
            return np.array([1.0, 0.0])
        return np.array([0.0, 1.0])  # last window

    monkeypatch.setattr(sim, "embed_wav", fake_embed)
    result = sim.long_form_drift(ref, gen, model=object())
    assert result["start_sim"] == pytest.approx(1.0)
    assert result["end_sim"] == pytest.approx(0.0)
    assert result["drift"] == pytest.approx(-1.0)
    assert result["drift_flagged"] is True
