# XploClone — Benchmark template (Phase 0 deliverable, PLAN-v2 §9)

Status: **TEMPLATE — NOT RUN.** No audio has been generated, no listener
has scored anything, no ElevenLabs comparison exists yet. Fill this in
at Gate 1 (English) and Gate 2 (Urdu). Do not fill it from memory or
from vendor claims.

## Comparators (record on the test date)

On the test date, check `elevenlabs.io/docs/overview/models` and record
which models actually list Urdu (screenshot or copy the page). Do not
rely on a September 2026 article: ElevenLabs v4/v4 Turbo launched
28 Sep 2026 claiming 90+ languages including Urdu, which outdated the
earlier "Urdu only on v3" claim (see AUDIT-v1 §A).

| System | Model (exact) | Date tested |
|---|---|---|
| XploClone EN | Chatterbox Turbo (git master 5de7a54), HF rev `749d1c1a…` | — |
| ElevenLabs EN | v4 Turbo | — |
| ElevenLabs EN (quality ref) | v4 | — |
| ElevenLabs UR | v4 Turbo (if Urdu listed) AND v3 | — |

## Test scripts (10 per variant, 30 total)

Write the scripts from `docs/recording-scripts/` (same content, so the
benchmark tests the voice the owner actually recorded). Per variant:
3 short (1 sentence), 4 medium (3–5 sentences), 3 long (1 paragraph),
covering: statements, questions, numbers, names, postcodes, recruitment
phrases (Xplogent), product phrases (xplosole), Urdu formal/informal.

Plus the **accent minimal set** (EN-US and EN-GB, same words, both
variants): car, park, bath, dance, schedule, tomato, herb, water,
better, about, laugh, grass, clerk, vase, leisure.

| # | Variant | Script (first line) | Audio hash (XploClone) | Audio hash (ElevenLabs) |
|---|---|---|---|---|
| 1 | en-us | — | — | — |
| … | … | … | … | … |
| 10 | en-us | — | — | — |
| 11–20 | en-gb | — | — | — |
| 21–30 | ur | — | — | — |

## Blind-test protocol

1. Generate every script with (a) XploClone, (b) ElevenLabs v4 Turbo,
   (c) ElevenLabs v3 (Urdu, and English as a quality reference),
   (d) ElevenLabs v4 (English, quality mode).
2. Randomise order, strip file metadata, blind the listeners.
3. Report the **first take**; note re-takes separately with the reason.
4. Listeners: owner + ≥ 2 native listeners per accent/language.
   Accent test: ≥ 2 native US + ≥ 2 native GB listeners, same 5
   sentences, rating "US / GB / neither / Pakistani" (not just "natural").

## Results (fill at Gate 1 / Gate 2)

| Metric | Target | XploClone | ElevenLabs | Pass? |
|---|---|---|---|---|
| Naturalness MOS (EN, 1–5) | ≥ v4 Turbo | — | — | — |
| Naturalness MOS (UR, 1–5) | > best ElevenLabs UR | — | — | — |
| Accent: US voice rated US | ≥ 3/4 listeners | — | — | — |
| Accent: GB voice rated GB | ≥ 3/4 listeners | — | — | — |
| Speaker similarity (cosine, **ECAPA-TDNN**) | ≥ 0.80 | — | — | — |
| Long-form drift (SIM start vs end, 2+ min) | \|drift\| ≤ 0.05 | — | — | — |
| WER EN (Whisper) | < 5% | — | — | — |
| WER UR (Whisper) | < 10% | — | — | — |
| Model TTFA p50 / p95 (prod GPU) | p95 < 200 ms | — | — | — |
| File complete ≤ 500 chars | < 2 s | — | — | — |
| Too-clean flag (acoustic profile: jitter/shimmer/HNR below reference band = flag) | no flag | — | — | — |
| Watermark survives 8 kHz μ-law | record pass/fail | — | — | — |

### Speaker similarity — how to measure it (gap A1/A2)

`scripts/benchmark/similarity.py` — no score is ever faked; if the
embedding cannot be computed, there is no SIM number.

```bash
python scripts/benchmark/similarity.py --ref ref-clean.wav --gen gen.wav
python scripts/benchmark/similarity.py --ref ref-clean.wav --gen long.wav --long-form
```

- **Embedding: ECAPA-TDNN** (SpeechBrain `spkrec-ecapa-voxceleb`),
  same model both sides. Every SIM number must name its embedding;
  a SIM without one is not comparable across runs.
- **Reference: the clean original recording only** — never a
  codec-reconstructed, μ-law, or re-encoded copy (that inflates SIM
  and hides drift). Both files must be 16 kHz mono WAV.
- **Target: SIM ≥ 0.80** (ECAPA-TDNN). SIM is a speaker check, not
  a quality check — a flat clone can score high SIM and sound wrong.
- **Long-form drift:** 2+ minute continuous sample, SIM of the
  first 30 s window vs the last 30 s window against the same
  reference. Report `drift = end − start`; |drift| > 0.05 is flagged
  for investigation (Qwen3-TTS: SIM 0.780 → 0.560 over 0–210 s,
  Lim et al., Oct 2026. The "~0.80 → ~0.52" figure is an
  approximate, model-specific illustration, not a measured
  Chatterbox result.)
- **Prosody is recorded per run:** preset + exaggeration / CFG /
  temperature / top_p / repetition_penalty, so a result can be
  reproduced. Same script, same preset, blind listeners.

### Acoustic profile — diagnose by acoustics (skill v2, gaps D1/D5)

`scripts/benchmark/acoustic_profile.py` — clone vs reference, same
text, same pipeline. Never judge connected speech against clinical
sustained-vowel norms; compare against the same speaker's connected
speech (and the §0 sustained-vowel baseline in the recording
scripts).

```bash
# Single file
python scripts/benchmark/acoustic_profile.py --wav file.wav
# Clone vs reference, same text, same pipeline
python scripts/benchmark/acoustic_profile.py --ref ref.wav --clone clone.wav
# F0 method: auto (pyin if librosa present, else built-in numpy
# autocorrelation), pyin (exits 2 naming librosa if missing), autocorr
python scripts/benchmark/acoustic_profile.py --wav file.wav --f0-method autocorr
```

Reports per file: mean F0, F0 SD (semitones), F0 range per
interpause stretch, jitter/shimmer (local, %), HNR (dB), H1–H2 (dB),
speaking/articulation rate (vowel-nucleus estimate), pause
count/total/% and % of pauses with breath (heuristic, unvalidated —
an audit signal, not ground truth). Unmeasurable = `null`, never 0.
Human bands for context (connected speech): F0 SD 1.8–5.4 st,
range 15–19 st per interpause stretch, pauses 11–32%, breath in
33–59% of pauses, articulation 4.0–4.7 syll/s. Too-clean flags
(compare mode): jitter/shimmer < 0.5× reference, HNR > reference
+ 3 dB, F0 SD < 1.5 st or < 0.5× reference, clone breath 0% while
the reference has breaths.

First measured run (2026-10-31, this VM, librosa pyin, Phase A
samples — different texts, so the compare is a code-path check
only, not a valid D5 result): api-en-us-his-voice.wav — mean F0
255.4 Hz, F0 SD 1.97 st, jitter 1.07%, shimmer 36.7%, HNR 10.39 dB,
articulation 4.4 syll/s, 1 pause (3.27%, 0% breath). Note: the
shimmer figure is far above clinical local-shimmer bands — it is
the estimator's pitch-synchronous value on noisy Nano CPU output,
so treat shimmer as a relative clone-vs-reference signal, not an
absolute clinical number, until the estimator is cross-checked
against Parselmouth/Praat.

### WER — a floor only, never a ranking (skill: evaluation)

WER (Whisper transcription vs script) is an intelligibility floor:
< 5% EN, < 10% UR. **WER must NEVER rank models.** TTSDS2 (over
11,000 human ratings) found WER only weakly and inconsistently
related to listener preference (Spearman ρ −0.11 to −0.45). That
sign is the *expected* sign for an error metric against MOS —
lower error should track higher preference — so the finding is
weakness/inconsistency, not a reversed law. Flat, over-articulated
speech can still score best on WER and sound worst. Naturalness is
decided by blind MOS listeners, not by WER.

### Too-clean flag (D5)

`scripts/benchmark/acoustic_profile.py` — flag any clone whose
jitter/shimmer/HNR sit *below* the reference speaker's band, not
just above pathology thresholds. A clone can pass SIM ≥ 0.80 and
still sound AI; this flag is the objective check that explains a
low naturalness score.

## Gates

- **Gate 1 (Phase 1 end):** English zero-shot wins blind test vs
  ElevenLabs v4 Turbo on ≥ 7/10 scripts per variant, accent test
  passes. If not: try Qwen3-TTS, then OpenF5-TTS, then fine-tune.
  If none passes, stop and re-plan.
- **Gate 2 (Phase 2 end):** Urdu passes vs the best ElevenLabs Urdu
  model on ≥ 7/10 scripts, WER < 10%. If not, ship English-only and
  record the reason here.
