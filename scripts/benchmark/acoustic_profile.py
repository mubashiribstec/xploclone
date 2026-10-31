"""Acoustic profile + "too clean" check (gaps D1/D5).

Profiles ONE wav file, or compares a clone vs a reference on the same
text with the identical pipeline. This is the voice-cloning skill's
"Diagnose by acoustics" table, implemented as code — it answers *why*
a clone sounds flat / robotic / lifeless, which SIM cannot: SIM is a
time-averaged embedding cosine, trained to be content- and
prosody-invariant, so a flat clone can score high SIM and still sound
wrong.

Usage:
    python scripts/benchmark/acoustic_profile.py --wav file.wav
    python scripts/benchmark/acoustic_profile.py --ref ref.wav --clone clone.wav
    python scripts/benchmark/acoustic_profile.py --wav file.wav --f0-method pyin

    --f0-method {auto,pyin,autocorr} (default auto): ``pyin`` uses
    librosa.pyin when librosa is installed; ``autocorr`` uses the
    built-in numpy autocorrelation tracker; ``auto`` tries pyin first
    and falls back to autocorr. The method actually used is reported
    in every output (``f0_method``) — compare-mode runs always use
    one method for both files.

Measures reported per file (all from the same pipeline):
    sample rate / duration / dtype (float32 in, float32 out)
    mean F0 (Hz); F0 SD (semitones, re the file's median F0);
    F0 range per interpause stretch (semitones, p95-p5, median
    across stretches); voiced fraction
    jitter (local, %): mean |T[i+1]-T[i]| / mean(T) over consecutive
        voiced frames, T = 1/F0, after a 3-frame median filter on the
        F0 contour (removes single-frame tracker noise; real F0 moves
        smoothly at a 10 ms hop). FRAME-based estimate, not Praat
        period-pulse jitter — comparable only within this pipeline.
    shimmer (local, %): same construction on pitch-synchronous
        amplitude — RMS over 3 local pitch periods per voiced frame.
        Frame-RMS shimmer is unusable at low F0 (a 10 ms frame holds
        ~1 period, so RMS oscillates with phase, not amplitude).
    HNR (dB): median over voiced frames of 10*log10(r/(1-r)), r =
        normalised autocorrelation at the pitch lag (Boersma-style).
        Capped at 40 dB (estimator ceiling); a capped value means
        "at least 40 dB".
    H1-H2 (dB): median over voiced frames of 20*log10(A1/A2), A1/A2 =
        FFT magnitudes at F0 / 2*F0. UNCORRECTED (no formant
        correction, H1*-H2*); per-frame median, same pipeline both sides.
    speaking rate: syllable estimate by vowel-nucleus envelope peaks
        (de Jong & Wempe style heuristic: intensity peaks in voiced
        speech, min 100 ms apart). Reported as articulation rate
        (syll/s over voiced time) and speaking rate (syll/s over total
        time). This is an ESTIMATE, not a transcript syllable count.
    pauses: count, total time, pause % of time, median pause, from a
        -40 dB (re peak-frame RMS) silence threshold, min pause 150 ms.
    breath: % of pauses (>= 200 ms) containing audible inhalation.
        HEURISTIC, not validated against labelled breaths: a pause
        counts as breath-containing if its RMS sits > ~10 dB above the
        file's noise floor AND its 2-6 kHz energy share exceeds 0.25.
        Digital silence scores 0% by design. Report the number, the
        method, and this limitation — never present it as a measured
        ground truth.

Human reference bands (voice-cloning skill v2, "Diagnose by acoustics"
+ references/what-makes-human.md; connected speech, NOT clinical
sustained-vowel norms):
    F0 SD ~1.8-5.4 semitones; < 1.5 st sounds flat regardless of SIM.
    F0 range per interpause stretch ~15-19 st.
    Pause time 11-32% of speech; breath in 33-59% of natural pauses.
    Speaking rate ~4.0-4.7 syll/s (articulation rate); within-speaker
    range 3.1-5.8 syll/s.
    A clone with jitter ~0.1% and HNR ~30 dB on connected speech is
    TOO CLEAN — below the human band. Clinical sustained-vowel
    thresholds (jitter <= ~1.04%, shimmer <= ~3.81%, HNR >= ~20 dB)
    are pathology thresholds, NEVER the target: they reject real
    connected speech, including real humans reading the same script.

Compare mode ("too clean" flag, gap D5):
    With a single reference file the "band" is the reference value
    with a tolerance (a proper band needs several reference takes).
    Flags fire when the clone sits BELOW the reference speaker's band:
      jitter:  clone < 0.5 x reference jitter
      shimmer: clone < 0.5 x reference shimmer
      HNR:     clone > reference HNR + 3 dB (cleaner = higher HNR;
               the too-clean direction for HNR is UP)
      F0 SD:   clone < 0.5 x reference, or clone < 1.5 st absolute
      breath:  reference has breaths and the clone has none
    ``too_clean`` is true if any of the jitter / shimmer / HNR flags
    fire. Deltas (clone - reference) are reported for every measure.
    RULE: compare clone vs reference on the SAME text, same pipeline.
    Comparing different speakers or different texts is invalid — the
    script cannot detect that, so the caller must guarantee it.

Failure policy (skill: never fake numbers):
- Missing file, unsupported format, or a file with no voiced frames
  for an F0 measure: the measure is null, never 0. A silent file
  profiles fine (pause % = 100, F0 measures null).
- ``--f0-method pyin`` without librosa installed: exit 2, error names
  librosa. The autocorr fallback is used only in ``auto`` mode, and
  only when it is the method actually reported.
- Nothing is ever synthesised, interpolated, or substituted to fill a
  missing measure.

Dependencies: numpy (BSD-3-Clause) + stdlib ``wave`` only, in the
default path. librosa (ISC licence) is optional and used only for
pyin when installed; Parselmouth/Praat are NOT required. The pure
functions work with numpy alone, so unit tests run in the test venv
with no audio libraries installed.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import wave
from pathlib import Path

import numpy as np

# Human reference bands, connected speech (skill v2). For context in
# output only — the too-clean flag compares clone vs reference, never
# against these bands alone.
HUMAN_BANDS = {
    "f0_sd_semitones": [1.8, 5.4],
    "f0_sd_flat_below_st": 1.5,
    "f0_range_per_interpause_st": [15.0, 19.0],
    "pause_pct": [11.0, 32.0],
    "breath_in_pauses_pct": [33.0, 59.0],
    "articulation_rate_syll_per_s": [4.0, 4.7],
    "articulation_rate_within_speaker_syll_per_s": [3.1, 5.8],
}

# Too-clean flag thresholds (compare mode; see module docstring).
TOO_CLEAN_JITTER_RATIO = 0.5
TOO_CLEAN_SHIMMER_RATIO = 0.5
TOO_CLEAN_HNR_DELTA_DB = 3.0

HNR_CEILING_DB = 40.0
SILENCE_THRESHOLD_DB = -40.0  # re peak-frame RMS
MIN_PAUSE_S = 0.15
MIN_BREATH_PAUSE_S = 0.20
MERGE_GAP_S = 0.05
F0_MIN_HZ = 50.0
F0_MAX_HZ = 500.0

BREATH_METHOD = (
    "heuristic: pause RMS > ~10 dB above file noise floor AND "
    "2-6 kHz energy share > 0.25; NOT validated against labelled breaths"
)
BREATH_LIMITATION = (
    "breath detection is a heuristic — digital silence scores 0% by design; "
    "treat the % as an audit signal, not a measured ground truth"
)
SYLLABLE_ESTIMATOR = (
    "vowel-nucleus envelope peaks (de Jong & Wempe style heuristic): "
    "intensity peaks in voiced speech, min 100 ms apart; estimate, not a "
    "transcript syllable count"
)


# ---------------------------------------------------------------- WAV input


def load_wav(path: str | Path) -> tuple[np.ndarray, int]:
    """Load a PCM WAV as mono float32 at its native sample rate.

    Accepts 8/16/24/32-bit PCM, mono or stereo (stereo is downmixed
    by channel mean — reported in the profile as ``channels``).
    No resampling: resampling inside a measurement script would make
    runs unreproducible. Returns (samples float32, sample_rate).
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"no such file: {path}")
    with wave.open(str(path), "rb") as wf:
        width = wf.getsampwidth()
        channels = wf.getnchannels()
        rate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)
    if width == 1:
        pcm = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif width == 2:
        pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif width == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        pcm = ((b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)) - (1 << 23)).astype(np.float32)
        pcm = pcm / float(1 << 23)
    elif width == 4:
        pcm = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / float(1 << 31)
    else:
        raise ValueError(f"{path}: unsupported sample width {width * 8}-bit (PCM 8/16/24/32 only)")
    if channels > 1:
        pcm = pcm.reshape(-1, channels).mean(axis=1)
    return np.ascontiguousarray(pcm, dtype=np.float32), rate


# ---------------------------------------------------------------- frames


def frame_rms(y: np.ndarray, sr: int, frame_s: float = 0.01) -> tuple[np.ndarray, np.ndarray]:
    """Per-frame RMS (10 ms frames by default) and frame centre times."""
    n = max(1, int(round(frame_s * sr)))
    n_frames = max(1, len(y) // n)
    padded = np.zeros(n_frames * n, dtype=np.float64)
    padded[: min(len(y), n_frames * n)] = y[: n_frames * n]
    trimmed = padded.reshape(n_frames, n)
    rms = np.sqrt(np.mean(trimmed.astype(np.float64) ** 2, axis=1))
    times = (np.arange(n_frames) + 0.5) * frame_s
    return rms.astype(np.float64), times


def _db(x: np.ndarray, ref: float) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(x, 1e-12) / max(ref, 1e-12))


# ---------------------------------------------------------------- F0


def estimate_f0_autocorr(
    y: np.ndarray, sr: int, frame_s: float = 0.05, hop_s: float = 0.010
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Numpy-only autocorrelation F0 tracker (fallback when librosa is absent).

    50 ms frames, 10 ms hop (a 25 ms frame holds ~3 periods at 120 Hz
    and the lag estimate wobbles frame to frame; 50 ms holds ~6 and
    is stable). Per frame: mean-removed autocorrelation (FFT), peak
    lag in [sr/500, sr/50] with parabolic interpolation, voiced if
    normalised peak > 0.45 and frame RMS is above the silence
    threshold. Returns (f0_hz with NaN for unvoiced, voiced mask,
    frame centre times). Documented fallback, not a silent
    substitute: the method used is reported as ``f0_method``.
    """
    frame_n = max(64, int(round(frame_s * sr)))
    hop_n = max(1, int(round(hop_s * sr)))
    if len(y) < frame_n:
        return np.array([]), np.array([], dtype=bool), np.array([])
    n_frames = 1 + (len(y) - frame_n) // hop_n
    f0 = np.full(n_frames, np.nan)
    voiced = np.zeros(n_frames, dtype=bool)
    times = (np.arange(n_frames) * hop_n + frame_n / 2) / sr
    min_lag = max(2, int(sr / F0_MAX_HZ))
    max_lag = min(frame_n - 2, int(sr / F0_MIN_HZ))
    nfft = 1 << int(math.ceil(math.log2(2 * frame_n)))
    rms_all, _ = frame_rms(y, sr)
    peak_rms = float(np.max(rms_all)) if len(rms_all) else 0.0
    for i in range(n_frames):
        seg = y[i * hop_n : i * hop_n + frame_n].astype(np.float64)
        seg = seg - seg.mean()
        rms = float(np.sqrt(np.mean(seg**2)))
        if rms <= 0.0 or peak_rms <= 0.0:
            continue
        if _db(np.array([rms]), peak_rms)[0] < SILENCE_THRESHOLD_DB:
            continue
        spec = np.fft.rfft(seg, n=nfft)
        ac = np.fft.irfft(spec * np.conj(spec))[: frame_n + 1]
        if ac[0] <= 0:
            continue
        ac = ac / ac[0]
        window = ac[min_lag : max_lag + 1]
        if len(window) == 0:
            continue
        k = int(np.argmax(window))
        if window[k] < 0.45:
            continue
        lag = min_lag + k
        # Parabolic interpolation around the peak.
        if 0 < k < len(window) - 1:
            a, b, c = window[k - 1], window[k], window[k + 1]
            denom = a - 2 * b + c
            shift = 0.5 * (a - c) / denom if denom != 0 else 0.0
            lag = lag + float(np.clip(shift, -0.5, 0.5))
        f0[i] = sr / lag
        voiced[i] = True
    return f0, voiced, times


def estimate_f0_pyin(y: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """F0 via librosa.pyin. Raises RuntimeError naming librosa if it is missing."""
    try:
        import librosa
    except ImportError as exc:  # noqa: BLE001 — message must name the fix
        raise RuntimeError(
            "librosa is not installed — cannot run pyin F0 estimation. "
            "Install it (pip install librosa) or re-run with "
            "--f0-method autocorr; do not report F0 numbers from a "
            "method that did not run."
        ) from exc
    f0, voiced_flag, _probs = librosa.pyin(
        y.astype(np.float32),
        fmin=F0_MIN_HZ,
        fmax=F0_MAX_HZ,
        sr=sr,
        frame_length=2048,
        hop_length=512,
    )
    f0 = np.asarray(f0, dtype=np.float64)
    voiced = np.asarray(voiced_flag, dtype=bool)
    times = librosa.times_like(f0, sr=sr, hop_length=512)
    return f0, voiced, times


def estimate_f0(
    y: np.ndarray, sr: int, method: str = "auto"
) -> tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    """F0 with the requested method. Returns (f0, voiced, times, method_used).

    ``auto`` tries librosa.pyin, falls back to the numpy
    autocorrelation tracker; ``pyin`` fails loudly if librosa is
    missing; ``autocorr`` always uses the built-in tracker.
    """
    if method == "pyin":
        return *estimate_f0_pyin(y, sr), "librosa.pyin"
    if method == "autocorr":
        return *estimate_f0_autocorr(y, sr), "autocorrelation"
    if method == "auto":
        try:
            return *estimate_f0_pyin(y, sr), "librosa.pyin"
        except RuntimeError:
            return *estimate_f0_autocorr(y, sr), "autocorrelation"
    raise ValueError(f"unknown f0 method {method!r} (auto, pyin, autocorr)")


# ---------------------------------------------------------------- micro-variation


def _median3(f0: np.ndarray) -> np.ndarray:
    """3-frame median filter on finite F0 values (tracker-noise removal)."""
    out = f0.copy()
    for i in range(1, len(f0) - 1):
        window = f0[i - 1 : i + 2]
        if np.all(np.isfinite(window)):
            out[i] = float(np.median(window))
    return out


def jitter_local_pct(f0: np.ndarray, voiced: np.ndarray) -> float | None:
    """Local jitter: mean |T[i+1]-T[i]| / mean(T) over consecutive voiced frames.

    F0 is median-filtered (3 frames) first — see _median3.
    """
    if len(f0) < 2:
        return None
    f0 = _median3(np.asarray(f0, dtype=np.float64))
    periods = 1.0 / f0
    diffs = []
    for i in range(len(f0) - 1):
        if voiced[i] and voiced[i + 1] and np.isfinite(periods[i]) and np.isfinite(periods[i + 1]):
            diffs.append(abs(periods[i + 1] - periods[i]))
    if not diffs:
        return None
    mean_period = float(np.nanmean(periods[voiced & np.isfinite(f0)]))
    if mean_period <= 0:
        return None
    return float(np.mean(diffs) / mean_period * 100.0)


def shimmer_local_pct(
    y: np.ndarray, sr: int, f0: np.ndarray, voiced: np.ndarray, times: np.ndarray
) -> float | None:
    """Local shimmer from pitch-synchronous amplitude.

    Per voiced frame: RMS over 3 local pitch periods centred on the
    frame. Shimmer = mean |A[i+1]-A[i]| / mean(A) over consecutive
    voiced frames. Three full periods make the amplitude independent
    of where the window starts in the cycle (frame-RMS shimmer is
    not — at 120 Hz a 10 ms frame holds ~1 period and RMS oscillates
    with phase, not amplitude).
    """
    if len(f0) == 0 or not np.any(voiced):
        return None
    amps: list[float] = []
    for i in np.where(voiced)[0]:
        f = f0[i]
        if not np.isfinite(f) or f <= 0:
            continue
        period_n = int(round(sr / f))
        win_n = 3 * period_n
        centre = int(round(times[i] * sr))
        start = max(0, centre - win_n // 2)
        seg = y[start : start + win_n].astype(np.float64)
        if len(seg) < win_n // 2:
            continue
        amps.append(float(np.sqrt(np.mean(seg**2))))
    if len(amps) < 2:
        return None
    amps_arr = np.array(amps)
    mean_amp = float(np.mean(amps_arr))
    if mean_amp <= 0:
        return None
    return float(np.mean(np.abs(np.diff(amps_arr))) / mean_amp * 100.0)


def hnr_db(
    y: np.ndarray, sr: int, f0: np.ndarray, voiced: np.ndarray, times: np.ndarray
) -> float | None:
    """Median HNR (dB) over voiced frames, autocorrelation method.

    Per voiced frame: r = normalised autocorrelation at the pitch lag;
    HNR = 10*log10(r/(1-r)). Capped at 40 dB (estimator ceiling).
    """
    if len(f0) == 0 or not np.any(voiced):
        return None
    frame_n = max(64, int(round(0.05 * sr)))
    values = []
    for i in np.where(voiced)[0]:
        f = f0[i]
        if not np.isfinite(f) or f <= 0:
            continue
        centre = int(round(times[i] * sr))
        start = max(0, centre - frame_n // 2)
        seg = y[start : start + frame_n].astype(np.float64)
        if len(seg) < frame_n // 2:
            continue
        seg = seg - seg.mean()
        lag = int(round(sr / f))
        if lag < 2 or lag >= len(seg):
            continue
        ac0 = float(np.dot(seg, seg))
        if ac0 <= 0:
            continue
        # Overlap-normalised autocorrelation at the pitch lag: both
        # sides use the SAME overlap, so a periodic signal scores
        # ~1.0 at its period regardless of lag (the biased form that
        # divides by the full-frame energy decays with lag and would
        # report ~6 dB for a pure tone — wrong).
        a = seg[:-lag]
        b = seg[lag:]
        denom = math.sqrt(float(np.dot(a, a)) * float(np.dot(b, b)))
        if denom <= 0:
            continue
        r = float(np.dot(a, b)) / denom
        if r <= 0.0:
            continue
        r = min(r, 0.9999)
        values.append(min(10.0 * math.log10(r / (1.0 - r)), HNR_CEILING_DB))
    if not values:
        return None
    return float(np.median(values))


def h1_h2_db(
    y: np.ndarray, sr: int, f0: np.ndarray, voiced: np.ndarray, times: np.ndarray
) -> float | None:
    """Median H1-H2 (dB) over voiced frames, UNCORRECTED (no formant correction).

    Per voiced frame: Hann-windowed FFT, magnitudes at the bins nearest
    F0 (H1) and 2*F0 (H2); H1-H2 = 20*log10(A1/A2). A pure tone has
    almost no 2nd harmonic, so H1-H2 is large positive — expected.
    """
    if len(f0) == 0 or not np.any(voiced):
        return None
    frame_n = max(256, int(round(0.05 * sr)))
    values = []
    for i in np.where(voiced)[0]:
        f = f0[i]
        if not np.isfinite(f) or f <= 0 or 2 * f >= sr / 2:
            continue
        centre = int(round(times[i] * sr))
        start = max(0, centre - frame_n // 2)
        seg = y[start : start + frame_n].astype(np.float64)
        if len(seg) < frame_n // 2:
            continue
        seg = seg * np.hanning(len(seg))
        spec = np.abs(np.fft.rfft(seg, n=frame_n * 2))
        freqs = np.fft.rfftfreq(frame_n * 2, d=1.0 / sr)
        a1 = float(spec[int(np.argmin(np.abs(freqs - f)))])
        a2 = float(spec[int(np.argmin(np.abs(freqs - 2 * f)))])
        if a1 <= 0 or a2 <= 0:
            continue
        values.append(20.0 * math.log10(a1 / a2))
    if not values:
        return None
    return float(np.median(values))


# ---------------------------------------------------------------- pauses / breath


def detect_pauses(rms: np.ndarray, times: np.ndarray) -> list[dict[str, float]]:
    """Silence stretches (frames > 40 dB below peak RMS), min 150 ms, gaps < 50 ms merged."""
    if len(rms) == 0:
        return []
    peak = float(np.max(rms))
    hop = float(times[1] - times[0]) if len(times) > 1 else 0.01
    if peak <= 0:
        end = float(times[-1] + hop / 2)
        return [{"start_s": 0.0, "end_s": round(end, 3), "duration_s": round(end, 3)}]
    silent = _db(rms, peak) < SILENCE_THRESHOLD_DB
    pauses: list[dict[str, float]] = []
    i = 0
    while i < len(silent):
        if not silent[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(silent) and silent[j + 1]:
            j += 1
        start = float(times[i] - hop / 2)
        end = float(times[j] + hop / 2)
        if end - start >= MIN_PAUSE_S:
            pauses.append(
                {
                    "start_s": round(max(start, 0.0), 3),
                    "end_s": round(end, 3),
                    "duration_s": round(end - max(start, 0.0), 3),
                }
            )
        i = j + 1
    # Merge pauses separated by < 50 ms of sound.
    merged: list[dict[str, float]] = []
    for p in pauses:
        if merged and p["start_s"] - merged[-1]["end_s"] < MERGE_GAP_S:
            merged[-1]["end_s"] = p["end_s"]
            merged[-1]["duration_s"] = round(p["end_s"] - merged[-1]["start_s"], 3)
        else:
            merged.append(dict(p))
    return merged


def pause_has_breath(
    y: np.ndarray, sr: int, pause: dict[str, float], noise_floor_rms: float
) -> bool:
    """Heuristic breath check for one pause (see BREATH_METHOD)."""
    start = int(pause["start_s"] * sr) + int(0.03 * sr)
    end = int(pause["end_s"] * sr) - int(0.03 * sr)
    if end - start < int(0.05 * sr):
        return False
    seg = y[start:end].astype(np.float64)
    rms = float(np.sqrt(np.mean(seg**2)))
    if rms <= 0 or noise_floor_rms <= 0:
        return False
    if rms < noise_floor_rms * 3.0:  # ~+10 dB above the file noise floor
        return False
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    freqs = np.fft.rfftfreq(len(seg), d=1.0 / sr)
    total = float(np.sum(spec**2))
    if total <= 0:
        return False
    hf = float(np.sum(spec[(freqs >= 2000) & (freqs <= 6000)] ** 2))
    return (hf / total) > 0.25


# ---------------------------------------------------------------- speaking rate


def syllable_nuclei_count(rms: np.ndarray, voiced_mask: np.ndarray) -> int:
    """Count vowel-nucleus envelope peaks (see SYLLABLE_ESTIMATOR).

    Smoothed (50 ms) RMS envelope, local maxima above a relative
    threshold, min 100 ms apart, inside voiced regions.
    """
    if len(rms) < 5:
        return 0
    kernel = np.ones(5) / 5.0
    env = np.convolve(rms, kernel, mode="same")
    voiced_mask = np.asarray(voiced_mask, dtype=bool)
    if len(voiced_mask) != len(env):
        idx = np.linspace(0, len(voiced_mask) - 1, len(env)).round().astype(int)
        voiced_mask = voiced_mask[idx]
    lo = float(np.median(env[voiced_mask])) if np.any(voiced_mask) else float(np.median(env))
    hi = float(np.percentile(env, 90))
    threshold = lo + 0.25 * max(hi - lo, 1e-12)
    min_dist = 10  # 100 ms at 10 ms frames
    count = 0
    last = -min_dist
    for i in range(1, len(env) - 1):
        if i - last < min_dist:
            continue
        if not voiced_mask[i]:
            continue
        if env[i] > env[i - 1] and env[i] >= env[i + 1] and env[i] > threshold:
            count += 1
            last = i
    return count


# ---------------------------------------------------------------- profile


def f0_stats(
    f0: np.ndarray, voiced: np.ndarray, times: np.ndarray, pauses: list[dict[str, float]]
) -> dict[str, object]:
    """Mean F0, SD in semitones, range per interpause stretch, voiced fraction."""
    voiced_f0 = f0[voiced & np.isfinite(f0)] if len(f0) else np.array([])
    if len(voiced_f0) == 0:
        return {
            "mean_hz": None,
            "sd_semitones": None,
            "range_per_interpause_stretch_st": None,
            "overall_range_st": None,
            "voiced_fraction": round(float(np.mean(voiced)) if len(voiced) else 0.0, 4),
        }
    median_f0 = float(np.median(voiced_f0))
    st = 12.0 * np.log2(voiced_f0 / median_f0)
    sd_st = float(np.std(st))
    overall_range = float(np.percentile(st, 95) - np.percentile(st, 5))
    # Interpause stretches: voiced F0 split at pause boundaries.
    ranges = []
    if len(times) == len(f0):
        mask = voiced & np.isfinite(f0)
        voiced_times = times[mask]
        end_t = float(times[-1]) if len(times) else 0.0
        bounds = [0.0] + [p["end_s"] for p in pauses] + [end_t]
        for a, b in zip(bounds[:-1], bounds[1:], strict=True):
            seg = voiced_f0[(voiced_times >= a) & (voiced_times < b)]
            if len(seg) >= 5:
                s = 12.0 * np.log2(seg / median_f0)
                ranges.append(float(np.percentile(s, 95) - np.percentile(s, 5)))
    return {
        "mean_hz": round(float(np.mean(voiced_f0)), 2),
        "sd_semitones": round(sd_st, 3),
        "range_per_interpause_stretch_st": round(float(np.median(ranges)), 3) if ranges else None,
        "overall_range_st": round(overall_range, 3),
        "voiced_fraction": round(float(np.mean(voiced)) if len(voiced) else 0.0, 4),
    }


def profile_wav(path: str | Path, f0_method: str = "auto") -> dict[str, object]:
    """Full acoustic profile of one WAV file. Never fakes a measure: unmeasurable = null."""
    y, sr = load_wav(path)
    duration = len(y) / sr if sr else 0.0
    f0, voiced, times, method_used = estimate_f0(y, sr, f0_method)
    rms, rms_times = frame_rms(y, sr)
    pauses = detect_pauses(rms, rms_times)
    total_pause = float(sum(p["duration_s"] for p in pauses))
    # Noise floor: median RMS of the quietest 10% of frames.
    noise_floor = float(np.median(np.sort(rms)[: max(1, len(rms) // 10)])) if len(rms) else 0.0
    breath_pauses = [p for p in pauses if p["duration_s"] >= MIN_BREATH_PAUSE_S]
    breath_count = sum(1 for p in breath_pauses if pause_has_breath(y, sr, p, noise_floor))
    # Voiced mask on the 10 ms RMS grid, for the syllable estimator.
    voiced_10ms = np.zeros(len(rms), dtype=bool)
    if len(times) and len(f0):
        idx = np.clip(
            (rms_times / (times[1] - times[0]) if len(times) > 1 else rms_times * 100)
            .round()
            .astype(int),
            0,
            len(f0) - 1,
        )
        voiced_10ms = voiced[idx]
    nuclei = syllable_nuclei_count(rms, voiced_10ms)
    voiced_time = float(np.sum(voiced_10ms) * 0.01)
    stats = f0_stats(f0, voiced, times, pauses)
    jitter = jitter_local_pct(f0, voiced)
    shimmer = shimmer_local_pct(y, sr, f0, voiced, times)
    hnr = hnr_db(y, sr, f0, voiced, times)
    h1h2 = h1_h2_db(y, sr, f0, voiced, times)
    return {
        "file": str(path),
        "sample_rate": sr,
        "duration_s": round(duration, 3),
        "dtype": "float32",
        "f0_method": method_used,
        "f0": stats,
        "jitter_local_pct": round(jitter, 4) if jitter is not None else None,
        "shimmer_local_pct": round(shimmer, 4) if shimmer is not None else None,
        "hnr_db": round(hnr, 2) if hnr is not None else None,
        "h1_h2_db": round(h1h2, 2) if h1h2 is not None else None,
        "speaking_rate": {
            "syllables_est": nuclei,
            "articulation_rate_syll_per_s": round(nuclei / voiced_time, 2)
            if voiced_time > 0
            else None,
            "speaking_rate_syll_per_s": round(nuclei / duration, 2) if duration > 0 else None,
            "estimator": SYLLABLE_ESTIMATOR,
        },
        "pauses": {
            "count": len(pauses),
            "total_s": round(total_pause, 3),
            "pause_pct": round(100.0 * total_pause / duration, 2) if duration > 0 else None,
            "median_s": round(float(np.median([p["duration_s"] for p in pauses])), 3)
            if pauses
            else None,
            "breath_pct": round(100.0 * breath_count / len(breath_pauses), 1)
            if breath_pauses
            else None,
            "breath_pauses_checked": len(breath_pauses),
            "breath_detection": {"method": BREATH_METHOD, "limitation": BREATH_LIMITATION},
        },
        "human_reference_bands_connected_speech": HUMAN_BANDS,
    }


# ---------------------------------------------------------------- compare


def _delta(clone_val: float | None, ref_val: float | None) -> float | None:
    if clone_val is None or ref_val is None:
        return None
    return round(float(clone_val) - float(ref_val), 4)


def too_clean_flags(ref: dict[str, object], clone: dict[str, object]) -> dict[str, object]:
    """D5 flags: clone below the reference speaker's band (see module docstring)."""
    r_jit = ref.get("jitter_local_pct")
    c_jit = clone.get("jitter_local_pct")
    r_shim = ref.get("shimmer_local_pct")
    c_shim = clone.get("shimmer_local_pct")
    r_hnr = ref.get("hnr_db")
    c_hnr = clone.get("hnr_db")
    r_f0sd = (ref.get("f0") or {}).get("sd_semitones") if isinstance(ref.get("f0"), dict) else None
    c_f0sd = (
        (clone.get("f0") or {}).get("sd_semitones") if isinstance(clone.get("f0"), dict) else None
    )
    r_breath = (
        (ref.get("pauses") or {}).get("breath_pct") if isinstance(ref.get("pauses"), dict) else None
    )
    c_breath = (
        (clone.get("pauses") or {}).get("breath_pct")
        if isinstance(clone.get("pauses"), dict)
        else None
    )

    jitter_flag = bool(
        isinstance(r_jit, (int, float))
        and isinstance(c_jit, (int, float))
        and r_jit > 0
        and c_jit < TOO_CLEAN_JITTER_RATIO * r_jit
    )
    shimmer_flag = bool(
        isinstance(r_shim, (int, float))
        and isinstance(c_shim, (int, float))
        and r_shim > 0
        and c_shim < TOO_CLEAN_SHIMMER_RATIO * r_shim
    )
    hnr_flag = bool(
        isinstance(r_hnr, (int, float))
        and isinstance(c_hnr, (int, float))
        and c_hnr > r_hnr + TOO_CLEAN_HNR_DELTA_DB
    )
    f0_flat_flag = bool(
        isinstance(c_f0sd, (int, float))
        and (
            c_f0sd < HUMAN_BANDS["f0_sd_flat_below_st"]
            or (isinstance(r_f0sd, (int, float)) and r_f0sd > 0 and c_f0sd < 0.5 * r_f0sd)
        )
    )
    breath_flag = bool(
        isinstance(r_breath, (int, float)) and r_breath > 0 and (c_breath is None or c_breath == 0)
    )
    return {
        "jitter_too_clean": jitter_flag,
        "shimmer_too_clean": shimmer_flag,
        "hnr_too_clean": hnr_flag,
        "f0_flat": f0_flat_flag,
        "no_breath": breath_flag,
        "too_clean": jitter_flag or shimmer_flag or hnr_flag,
        "rule": (
            "clone below reference band: jitter/shimmer < 0.5x ref; "
            "HNR > ref + 3 dB (cleaner is higher); F0 SD < 1.5 st or "
            "< 0.5x ref; breath 0% while reference has breaths"
        ),
    }


def compare_profiles(
    ref_path: str | Path, clone_path: str | Path, f0_method: str = "auto"
) -> dict[str, object]:
    """Clone vs reference, same text, same pipeline. Deltas are clone - reference."""
    ref = profile_wav(ref_path, f0_method)
    clone = profile_wav(clone_path, f0_method)
    r_f0 = ref["f0"] if isinstance(ref["f0"], dict) else {}
    c_f0 = clone["f0"] if isinstance(clone["f0"], dict) else {}
    r_sp = ref["speaking_rate"] if isinstance(ref["speaking_rate"], dict) else {}
    c_sp = clone["speaking_rate"] if isinstance(clone["speaking_rate"], dict) else {}
    r_pa = ref["pauses"] if isinstance(ref["pauses"], dict) else {}
    c_pa = clone["pauses"] if isinstance(clone["pauses"], dict) else {}
    return {
        "reference": ref,
        "clone": clone,
        "deltas_clone_minus_reference": {
            "f0_mean_hz": _delta(c_f0.get("mean_hz"), r_f0.get("mean_hz")),
            "f0_sd_semitones": _delta(c_f0.get("sd_semitones"), r_f0.get("sd_semitones")),
            "f0_range_per_interpause_st": _delta(
                c_f0.get("range_per_interpause_stretch_st"),
                r_f0.get("range_per_interpause_stretch_st"),
            ),
            "jitter_local_pct": _delta(clone.get("jitter_local_pct"), ref.get("jitter_local_pct")),
            "shimmer_local_pct": _delta(
                clone.get("shimmer_local_pct"), ref.get("shimmer_local_pct")
            ),
            "hnr_db": _delta(clone.get("hnr_db"), ref.get("hnr_db")),
            "h1_h2_db": _delta(clone.get("h1_h2_db"), ref.get("h1_h2_db")),
            "articulation_rate_syll_per_s": _delta(
                c_sp.get("articulation_rate_syll_per_s"), r_sp.get("articulation_rate_syll_per_s")
            ),
            "pause_pct": _delta(c_pa.get("pause_pct"), r_pa.get("pause_pct")),
            "breath_pct": _delta(c_pa.get("breath_pct"), r_pa.get("breath_pct")),
        },
        "flags": too_clean_flags(ref, clone),
        "note": (
            "Valid only when clone and reference are the SAME text, same "
            "speaker, same pipeline. Different speakers/texts invalidate "
            "the comparison — the script cannot detect that."
        ),
    }


# ---------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Acoustic profile of one WAV, or clone-vs-reference compare (gaps D1/D5)."
    )
    parser.add_argument("--wav", help="single WAV file to profile")
    parser.add_argument("--ref", help="reference WAV (compare mode, with --clone)")
    parser.add_argument("--clone", help="clone WAV (compare mode, with --ref)")
    parser.add_argument(
        "--f0-method",
        default="auto",
        choices=["auto", "pyin", "autocorr"],
        help="F0 estimator: auto (pyin if librosa installed, else autocorrelation), "
        "pyin (librosa, fails loudly if missing), autocorr (built-in numpy tracker)",
    )
    args = parser.parse_args(argv)
    try:
        if args.wav and (args.ref or args.clone):
            raise ValueError("use either --wav (single) or --ref + --clone (compare), not both")
        if args.wav:
            result = profile_wav(args.wav, args.f0_method)
        elif args.ref and args.clone:
            result = compare_profiles(args.ref, args.clone, args.f0_method)
        else:
            raise ValueError("need --wav, or both --ref and --clone")
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
