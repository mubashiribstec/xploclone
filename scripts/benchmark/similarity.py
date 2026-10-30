"""Speaker-similarity (SIM) + long-form drift measurement (gap A1/A2).

Usage:
    python scripts/benchmark/similarity.py --ref ref.wav --gen gen.wav
    python scripts/benchmark/similarity.py --ref ref.wav --gen long.wav --long-form

What it measures: cosine similarity between speaker embeddings of a
reference recording and generated audio. The embedding model is NAMED
in every output (default ``ecapa-tdnn`` — SpeechBrain ECAPA-TDNN,
``speechbrain/spkrec-ecapa-voxceleb``) and must be the SAME model on
both sides; a SIM number without its embedding is meaningless and
must never be reported as one.

Rules (skill: evaluation):
- The reference MUST be the clean original recording — never a
  codec-reconstructed, μ-law, or re-encoded copy. A reconstructed
  reference inflates SIM and hides real drift.
- SIM >= 0.80 (ECAPA-TDNN) is the Gate 1 target. SIM is a speaker
  check, not a quality check: a flat, robotic clone can score high
  SIM and still sound wrong. Naturalness is judged by blind MOS
  listeners (docs/BENCHMARK.md), never by SIM alone.
- WER is a floor only (intelligibility): WER < 5% EN / < 10% UR.
  WER must NEVER rank models — a 2026 study (~11,800 human ratings)
  found WER negatively correlated with listener preference
  (Spearman rho approx -0.11 to -0.45): flat over-articulated speech
  scores best on WER and sounds worst.
- Long-form drift: a 2+ minute continuous sample is split into a
  first-30s and last-30s window; SIM is computed for each against
  the same reference. ``drift = end - start``; |drift| > 0.05 is
  flagged for investigation (vendor reports show SIM falling from
  ~0.80 to ~0.52 over minutes on some systems — that is the failure
  this test exists to catch).

Dependencies: numpy + the embedding backend. The backend is imported
LAZILY — the pure functions (cosine, drift, WAV loading) work
without torch/SpeechBrain, so unit tests run on CPU with no model
download. ``similarity()`` raises a clear error if SpeechBrain is
not installed instead of silently substituting a weaker metric.
No score is ever faked: if the embedding cannot be computed, there
is no SIM number.
"""

from __future__ import annotations

import argparse
import json
import sys
import wave
from pathlib import Path

import numpy as np

EMBEDDING = "ecapa-tdnn"
ECAPA_SOURCE = "speechbrain/spkrec-ecapa-voxceleb"
SAMPLE_RATE = 16000
DRIFT_FLAG_THRESHOLD = 0.05


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two 1-D embedding vectors."""
    a = np.asarray(a, dtype=np.float64).ravel()
    b = np.asarray(b, dtype=np.float64).ravel()
    if a.shape != b.shape:
        raise ValueError(f"embedding shapes differ: {a.shape} vs {b.shape}")
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))
    if norm_a == 0.0 or norm_b == 0.0:
        raise ValueError("zero-norm embedding — cannot compute similarity")
    return float(np.dot(a, b) / (norm_a * norm_b))


def load_wav_mono_16k(path: str | Path) -> np.ndarray:
    """Load a 16-bit PCM WAV as mono float32 at 16 kHz.

    Strict on purpose: the embedding expects 16 kHz mono. A file at
    another rate is an error, not a silent resample — resampling
    inside a measurement script would make runs unreproducible.
    Convert with ``sox``/``ffmpeg`` to 16 kHz mono first.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"no such file: {path}")
    with wave.open(str(path), "rb") as wf:
        if wf.getsampwidth() != 2:
            raise ValueError(
                f"{path}: only 16-bit PCM WAV is supported (got {wf.getsampwidth() * 8}-bit)"
            )
        if wf.getnchannels() != 1:
            raise ValueError(
                f"{path}: only mono WAV is supported (got {wf.getnchannels()} channels)"
            )
        if wf.getframerate() != SAMPLE_RATE:
            raise ValueError(
                f"{path}: expected {SAMPLE_RATE} Hz, got {wf.getframerate()} Hz — "
                "convert to 16 kHz mono first"
            )
        frames = wf.readframes(wf.getnframes())
    pcm = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
    return pcm / 32768.0


def window_samples(samples: np.ndarray, window_s: float = 30.0) -> tuple[np.ndarray, np.ndarray]:
    """First and last ``window_s`` seconds of a sample array."""
    n = int(window_s * SAMPLE_RATE)
    if len(samples) < 2 * n:
        raise ValueError(
            f"audio is {len(samples) / SAMPLE_RATE:.1f}s — long-form drift needs "
            f"at least {2 * window_s:.0f}s (two {window_s:.0f}s windows)"
        )
    return samples[:n], samples[-n:]


def drift_report(start_sim: float, end_sim: float) -> dict[str, object]:
    """Drift between start-of-clip and end-of-clip SIM."""
    drift = end_sim - start_sim
    return {
        "start_sim": round(start_sim, 4),
        "end_sim": round(end_sim, 4),
        "drift": round(drift, 4),
        "drift_flagged": abs(drift) > DRIFT_FLAG_THRESHOLD,
        "threshold": DRIFT_FLAG_THRESHOLD,
    }


def load_embedding_model(embedding: str = EMBEDDING):  # type: ignore[no-untyped-def]
    """Load the named speaker-embedding model (lazy import).

    Only ``ecapa-tdnn`` is wired: SpeechBrain ECAPA-TDNN. Any other
    name is an error — silently swapping in a different embedding
    would make SIM numbers incomparable across runs.
    """
    if embedding != EMBEDDING:
        raise ValueError(f"unsupported embedding {embedding!r} (only {EMBEDDING!r} is wired)")
    try:
        from speechbrain.inference import EncoderClassifier
    except ImportError as exc:  # noqa: BLE001 — message must name the fix
        raise RuntimeError(
            "SpeechBrain is not installed — cannot compute speaker similarity. "
            "Install it (pip install speechbrain torch) and re-run; "
            "do not substitute another metric and call it SIM."
        ) from exc
    return EncoderClassifier.from_hparams(source=ECAPA_SOURCE)


def embed_wav(model, samples: np.ndarray) -> np.ndarray:  # type: ignore[no-untyped-def]
    """Embed 16 kHz mono float32 samples with a loaded model."""
    import torch

    tensor = torch.from_numpy(samples).unsqueeze(0)
    with torch.no_grad():
        embedding = model.encode_batch(tensor)
    return embedding.squeeze().cpu().numpy().astype(np.float64)


def similarity(
    ref_path: str | Path,
    gen_path: str | Path,
    embedding: str = EMBEDDING,
    model=None,  # type: ignore[no-untyped-def]
) -> dict[str, object]:
    """SIM between a clean reference and generated audio (named embedding)."""
    ref = load_wav_mono_16k(ref_path)
    gen = load_wav_mono_16k(gen_path)
    model = model if model is not None else load_embedding_model(embedding)
    score = cosine_similarity(embed_wav(model, ref), embed_wav(model, gen))
    return {"embedding": embedding, "similarity": round(score, 4), "target": 0.80}


def long_form_drift(
    ref_path: str | Path,
    gen_path: str | Path,
    window_s: float = 30.0,
    embedding: str = EMBEDDING,
    model=None,  # type: ignore[no-untyped-def]
) -> dict[str, object]:
    """SIM at the start vs the end of a 2+ minute generated sample."""
    ref = load_wav_mono_16k(ref_path)
    gen = load_wav_mono_16k(gen_path)
    model = model if model is not None else load_embedding_model(embedding)
    ref_emb = embed_wav(model, ref)
    first, last = window_samples(gen, window_s)
    report = drift_report(
        cosine_similarity(ref_emb, embed_wav(model, first)),
        cosine_similarity(ref_emb, embed_wav(model, last)),
    )
    return {"embedding": embedding, "window_s": window_s, **report}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Speaker similarity (SIM) and long-form drift vs a clean reference."
    )
    parser.add_argument(
        "--ref",
        required=True,
        help="clean original reference WAV (16 kHz mono, never codec-reconstructed)",
    )
    parser.add_argument("--gen", required=True, help="generated WAV (16 kHz mono)")
    parser.add_argument(
        "--embedding", default=EMBEDDING, help=f"embedding model (only {EMBEDDING!r} is wired)"
    )
    parser.add_argument(
        "--long-form",
        action="store_true",
        help="2+ minute drift test: SIM first vs last 30 s window",
    )
    parser.add_argument(
        "--window-s", type=float, default=30.0, help="drift window in seconds (default 30)"
    )
    args = parser.parse_args(argv)
    try:
        if args.long_form:
            result = long_form_drift(args.ref, args.gen, args.window_s, args.embedding)
        else:
            result = similarity(args.ref, args.gen, args.embedding)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
