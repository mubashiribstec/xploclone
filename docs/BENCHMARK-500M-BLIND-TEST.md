# XploClone — Full Chatterbox 500M vs Turbo blind test (PREPARATION ONLY)

Status: **PREPARATION — DO NOT RUN.** This document sets up the test.
No audio has been generated for it, no model has been run, no listener
has scored anything. Do not run any part of it on this 2-core CPU VM —
see GPU requirement below.

## Why this test exists

Chatterbox Turbo (the engine XploClone ships, `ChatterboxTTS` in
`inference_turbo` mode, pinned wheel 0.1.7 / git master `5de7a54`)
**ignores the prosody knobs**: `exaggeration` has no effect in Turbo
mode and `cfg_weight` is hardcoded to `0.0` in `inference_turbo`
(verified from the wheel source; see `api/engine.py:16–22` and
`api/engine.py:137–143` — the build records exaggeration/CFG as
"not effective on Turbo 0.1.7"). The full ChatterboxTTS 500M model
(`ChatterboxTTS.generate`) **honours** `exaggeration` and `cfg_weight`
(defaults 0.5 / 0.5).

Consequence: the presets in the web UI / API (exaggeration, CFG,
temperature, top_p, repetition_penalty) may only get an audible effect
on the full 500M model. If the 500M model wins this blind test, the
presets become real controls and the 500M model becomes the file-
generation engine candidate; if Turbo wins or ties, the presets stay
decorative on Turbo and the 500M model is not adopted on quality
grounds alone. This test decides that — it does not assume it.

## The three versions (same script, same reference, same day)

| Version | Model (record exact revision on test day) | Presets |
|---|---|---|
| A | Chatterbox Turbo, 350M — pinned wheel 0.1.7, git master `5de7a54`, HF rev `749d1c1a…` (same pin as `docs/BENCHMARK.md`) | Default preset (exaggeration/CFG recorded as not effective) |
| B | Full ChatterboxTTS, 500M — `ResembleAI/chatterbox`, record repo + HF revision + commit on test day | Same preset values as A, recorded per run (exaggeration / CFG / temperature / top_p / repetition_penalty) |
| C | ElevenLabs v4 Turbo — record exact model name from `elevenlabs.io/docs/overview/models` on test day | Default stability/similarity settings, recorded |

Record on test day, for each version: model name, repo/revision/
commit, library version, hardware (GPU model, VRAM), reference file
hash, preset values used, date. A result without the revision is not
a result.

## Test scripts (10 per variant)

Reuse the `docs/BENCHMARK.md` script set: 10 scripts per variant
(3 short / 4 medium / 3 long, covering statements, questions,
numbers, names, postcodes, recruitment phrases, product phrases),
plus the **accent minimal set** (EN-US and EN-GB, same words, both
variants): car, park, bath, dance, schedule, tomato, herb, water,
better, about, laugh, grass, clerk, vase, leisure.

Run the same 10 scripts per variant for all three versions — 30
scripts × 3 versions = 90 clips per variant (en-us, en-gb).
Urdu is out of scope for this test (Urdu engine is gated by the
spike; Gate 2 covers it separately).

## Reference recordings required

- **60 s proxy minimum** per variant (en-us, en-gb) to run the test
  at all — same session, same mic/gain, 48 kHz 16-bit mono WAV,
  single speaker, quiet room.
- **20 min full sets** per variant before Gate 1 — the full recording
  scripts (`docs/recording-scripts/en-us.md`, `en-gb.md`), including
  the sustained-vowel baseline (D2) and the prosody block (D3) if
  recorded by then.
- Reference file hash recorded in the results table; the clean
  original recording only — never a codec-reconstructed copy — is
  the SIM reference.

## Blind protocol

1. Generate every script with all three versions, first take only;
   note re-takes separately with the reason.
2. Randomise clip order; assign random IDs; strip file metadata.
3. Keep the version→ID mapping in a private file until scoring is
   complete. Listeners never see model names, file names, or
   generation order.
4. Same text, same reference, same day for all three versions —
   no version gets a better reference or a fresher recording.

## Listeners

- Owner + ≥ 2 native listeners per accent (≥ 2 native US for en-us,
  ≥ 2 native GB for en-gb).
- Accent question per clip: "US / GB / neither / Pakistani".
- Familiar-listener rule applies: the owner is the strictest judge
  of "sounds like me" — his vote is reported separately, not
  averaged away.

## Scoring sheet (per clip)

| Field | Scale |
|---|---|
| Naturalness | 1–5 |
| Accent | US / GB / neither / Pakistani |
| "Sounds like the owner" | yes / no |
| "Too clean / lifeless / AI-sounding" | yes / no (the D5 question — asked explicitly, not inferred from naturalness) |
| Notes | free text (flat? robotic? wrong emphasis? sibilants?) |

## Objective columns (same pipeline both sides)

| Column | Method |
|---|---|
| SIM (ECAPA-TDNN) | `scripts/benchmark/similarity.py`, same embedding all versions, clean reference only |
| WER | Whisper transcription vs script — **floor only** (< 5% EN). Never ranks versions (TTSDS2, over 11,000 ratings: ρ −0.11 to −0.45, weak/inconsistent) |
| F0 / acoustic profile | `scripts/benchmark/acoustic_profile.py` — mean F0, F0 SD/range, jitter/shimmer/HNR vs reference band; the D5 too-clean flag |
| Long-form drift | SIM first 30 s vs last 30 s of a 2+ min continuous sample; \|drift\| > 0.05 flagged (Qwen3-TTS 0.780 → 0.560 over 0–210 s, Lim et al., Oct 2026, is the published drift pattern — the "~0.80 → ~0.52" figure is an approximate, model-specific illustration) |
| Latency | Model TTFA p50/p95 on the test GPU (500M will be slower than Turbo — record it, do not assume it) |

## Pass criteria

- **Gate 1 (this test feeds it):** a version wins ≥ 7/10 scripts
  per variant vs ElevenLabs v4 Turbo on blind naturalness (owner +
  ≥ 2 natives per accent), accent test passes (≥ 3/4 listeners per
  accent), SIM ≥ 0.80 (ECAPA-TDNN), no too-clean flag.
- **500M adoption rule:** full 500M is adopted as the file-generation
  engine only if it beats Turbo on blind naturalness by ≥ 7/10
  scripts per variant **and** the preset effect is audible (same
  script at two exaggeration/CFG settings scores differently by
  listeners). If 500M ties Turbo, Turbo stays (lower latency, known
  pin); if Turbo wins, 500M is dropped for this voice.
- **If neither beats v4 Turbo:** try Qwen3-TTS, then OpenF5-TTS,
  then fine-tune (PLAN-v2 §9.3 Gate 1 order). Do not fine-tune
  before measuring zero-shot.

## GPU requirement — do NOT run on this VM

500M synthesis needs a GPU. **This test is explicitly NOT runnable
on the 2-core CPU VM where this document was written — do not
attempt it there.** Turbo on CPU is already slow (Nano CPU sample
run, 31 Oct 2026: 27.2 s for 4.88 s audio); a 500M autoregressive
model on 2 CPU cores would take orders of magnitude longer per clip
and prove nothing about quality. Run it on the GPU host (production
GPU or rented GPU) with the pinned revisions above.

## Do not run until — checklist

- [ ] 60 s proxy recordings done per variant (en-us, en-gb), 48 kHz
      16-bit mono WAV, single speaker, quiet room.
- [ ] 20 min full recording sets done per variant (before Gate 1).
- [ ] GPU host ready (GPU model + VRAM recorded; CUDA driver
      verified; Chatterbox full 500M installs and generates).
- [ ] Full 500M repo + HF revision recorded (do not run on an
      unpinned checkout).
- [ ] ElevenLabs v4 Turbo availability confirmed on test day
      (check `elevenlabs.io/docs/overview/models`).
- [ ] `scripts/benchmark/acoustic_profile.py` built (D1 — in
      progress by a parallel agent) and `scripts/benchmark/
      similarity.py` verified on the test GPU.
- [ ] Blind-test harness ready (`scripts/benchmark/
      generate_benchmark.py` — random IDs, metadata stripped,
      private mapping, score sheet, first-take rule).
- [ ] Listeners confirmed (owner + ≥ 2 natives per accent).
