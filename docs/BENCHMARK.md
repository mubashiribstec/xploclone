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
| XploClone EN | Chatterbox Turbo 0.1.7, HF rev `749d1c1a…` | — |
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
  for investigation (vendor reports show SIM falling ~0.80 → ~0.52
  over minutes on some systems).
- **Prosody is recorded per run:** preset + exaggeration / CFG /
  temperature / top_p / repetition_penalty, so a result can be
  reproduced. Same script, same preset, blind listeners.

### WER — a floor only, never a ranking (skill: evaluation)

WER (Whisper transcription vs script) is an intelligibility floor:
< 5% EN, < 10% UR. **WER must NEVER rank models.** A 2026 study
(~11,800 human ratings) found WER negatively correlated with
listener preference (Spearman ρ ≈ −0.11 to −0.45): flat,
over-articulated speech scores best on WER and sounds worst.
Naturalness is decided by blind MOS listeners, not by WER.

## Gates

- **Gate 1 (Phase 1 end):** English zero-shot wins blind test vs
  ElevenLabs v4 Turbo on ≥ 7/10 scripts per variant, accent test
  passes. If not: try Qwen3-TTS, then OpenF5-TTS, then fine-tune.
  If none passes, stop and re-plan.
- **Gate 2 (Phase 2 end):** Urdu passes vs the best ElevenLabs Urdu
  model on ≥ 7/10 scripts, WER < 10%. If not, ship English-only and
  record the reason here.
