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
| Speaker similarity (cosine) | ≥ 0.80 | — | — | — |
| WER EN (Whisper) | < 5% | — | — | — |
| WER UR (Whisper) | < 10% | — | — | — |
| Model TTFA p50 / p95 (prod GPU) | p95 < 200 ms | — | — | — |
| File complete ≤ 500 chars | < 2 s | — | — | — |
| Watermark survives 8 kHz μ-law | record pass/fail | — | — | — |

## Gates

- **Gate 1 (Phase 1 end):** English zero-shot wins blind test vs
  ElevenLabs v4 Turbo on ≥ 7/10 scripts per variant, accent test
  passes. If not: try Qwen3-TTS, then OpenF5-TTS, then fine-tune.
  If none passes, stop and re-plan.
- **Gate 2 (Phase 2 end):** Urdu passes vs the best ElevenLabs Urdu
  model on ≥ 7/10 scripts, WER < 10%. If not, ship English-only and
  record the reason here.
