"""Blind-test harness (PLAN-v2 §9.2) — manifest, randomisation, scoring.

Usage:
    python scripts/benchmark/generate_benchmark.py \
        --xploclone-dir outputs/xploclone \
        --elevenlabs-dir outputs/elevenlabs \
        --out outputs/blind-test

What it does:
1. Reads WAV files from the two dirs (names like ``en-us_03.wav``).
   It never reads or stores API keys; the audio files must already exist
   (generate the ElevenLabs side with your own key, outside this repo).
2. Copies them to ``<out>/clips/`` renamed to blind IDs (``clip-001.wav``
   …), stripping file metadata by re-writing the WAV (no tags, no
   filenames that reveal the source).
3. Writes ``manifest.csv`` (blind_id, variant, script_no, source) and a
   ``score-sheet.csv`` template for listeners (naturalness 1–5, accent
   US/GB/neither/Pakistani, "sounds like Mubashir" yes/no).
4. Writes ``wer.py`` usage notes: transcribe with Whisper and compare
   to the script text for the WER column in docs/BENCHMARK.md.

The mapping file (blind_id -> source) is the ONLY place the truth lives.
Keep it private until scoring is done, then publish it with the results.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import random
import wave
from pathlib import Path


def _rewrite_wav(src: Path, dst: Path) -> str:
    """Copy audio samples into a fresh WAV (drops metadata/chunks)."""
    with wave.open(str(src), "rb") as inp:
        params = inp.getparams()
        frames = inp.readframes(inp.getnframes())
    with wave.open(str(dst), "wb") as out:
        out.setparams(params)
        out.writeframes(frames)
    return hashlib.sha256(frames).hexdigest()[:16]


def build_blind_test(
    xploclone_dir: Path, elevenlabs_dir: Path, out: Path, seed: int = 20261030
) -> Path:
    clips_dir = out / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, str]] = []
    for source_dir, source in ((xploclone_dir, "xploclone"), (elevenlabs_dir, "elevenlabs")):
        for wav in sorted(source_dir.glob("*.wav")):
            stem = wav.stem  # e.g. en-us_03
            variant, _, script_no = stem.partition("_")
            entries.append(
                {
                    "path": str(wav),
                    "source": source,
                    "variant": variant,
                    "script_no": script_no,
                }
            )
    rng = random.Random(seed)
    rng.shuffle(entries)
    manifest: list[dict[str, str]] = []
    for i, entry in enumerate(entries, start=1):
        blind_id = f"clip-{i:03d}"
        audio_hash = _rewrite_wav(Path(entry["path"]), clips_dir / f"{blind_id}.wav")
        manifest.append(
            {
                "blind_id": blind_id,
                "variant": entry["variant"],
                "script_no": entry["script_no"],
                "source": entry["source"],
                "audio_hash": audio_hash,
            }
        )
    with open(out / "manifest.csv", "w", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["blind_id", "variant", "script_no", "source", "audio_hash"]
        )
        writer.writeheader()
        writer.writerows(manifest)
    with open(out / "score-sheet.csv", "w", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "blind_id",
                "variant",
                "listener",
                "naturalness_1_5",
                "accent_us_gb_neither_pakistani",
                "sounds_like_mubashir",
                "notes",
            ],
        )
        writer.writeheader()
        for row in manifest:
            writer.writerow(
                {
                    "blind_id": row["blind_id"],
                    "variant": row["variant"],
                    "listener": "",
                    "naturalness_1_5": "",
                    "accent_us_gb_neither_pakistani": "",
                    "sounds_like_mubashir": "",
                    "notes": "",
                }
            )
    return out / "manifest.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xploclone-dir", required=True, type=Path)
    parser.add_argument("--elevenlabs-dir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=20261030)
    args = parser.parse_args()
    manifest = build_blind_test(args.xploclone_dir, args.elevenlabs_dir, args.out, seed=args.seed)
    print(f"Blind test built: {manifest}")


if __name__ == "__main__":
    main()
