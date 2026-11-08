# XploClone — Urdu research spike (TEMPLATE, PLAN-v2 §4.1)

Status: **DONE 2026-10-31 — verdict FAIL (see `~/workspace/xploclone/URDU-SPIKE-RESULT.md`).** DeepSpeak-v1 generates intelligible Urdu but does not clone the owner's voice (ECAPA SIM 0.06–0.16); Kani-UR/Piper are fixed voices; Dia-1.6B-Urdu loads but its cloning is untested (CPU impractical — needs a GPU run).
Time-box: 1 week, parallel to the English MVP (Phase 1).
Goal: answer with evidence, "can any licensed, downloadable model clone
Mubashir's Urdu voice at acceptable quality, or not?"

**Rules:**
- No candidate passes without: exact repo URL, licence file, checkpoint
  hash, and a 30-second Urdu sample. A lead without a download is a FAIL.
- Shipping a Hindi voice or a generic Urdu voice as `mubashir-ur` is
  **forbidden**. If the spike fails, v1 ships English-only (Fallback C).
- Urdu script is the gate; Roman Urdu is a 500-word stretch (§4.3).
  Full Roman Urdu transliteration is Phase 2, not v1.

> **Standing rule — diacritics (added 2026-10-31, Gap D4; does not
> change the spike verdict or results above):** any future Urdu
> recording or generation from a script must use fully vocalised
> text — every Urdu script line carries full diacritics (zabar َ,
> zer ِ, pesh ُ, shadd ّ, jazm ْ wherever they change the reading) +
> a Roman/IPA gloss, with homographs disambiguated in context before
> recording. Urdu Nastaliq normally omits most vowel diacritics, so
> the same consonant skeleton can be read several ways; PronouncUR
> G2P is only ~64% accurate on undiacritised text, so undiacritised
> text is ambiguous text. **Never record or generate from
> undiacritised Nastaliq alone.** A mispronunciation that comes from
> an ambiguous line is a text problem, not a model problem — do not
> blame the model for it. (Same rule now stands at the top of
> `docs/recording-scripts/ur.md`.)

## 1. Kani-TTS Urdu

| Field | Value |
|---|---|
| HF repo URL (exact, Urdu variant — not just `niobures/Kani-TTS`) | — |
| Licence file | — |
| Checkpoint hash | — |
| Languages listed in the model card | — |
| 30-second Urdu sample generated? (hash) | — |
| Verdict | — |

Note: Kani-TTS base is Apache-2.0 and officially supports English,
Spanish, Kyrgyz (v2). Urdu is a *community adaptation*, not an official
language. If no Urdu repo / licence / checkpoint can be found, this
candidate **fails** — record why and move on.

## 2. DeepSpeak-v1

| Field | Value |
|---|---|
| Public checkpoint / repo URL | — |
| Licence | — |
| Author contacted? (date, reply) | — |
| Verdict | — |

Note: DeepSpeak-v1 is known only from the author's CV/portfolio
(rectified-flow DiT, Qwen3.5-0.8B backbone, cloning from 3–15 s clips).
No public checkpoint was found in PLAN-v2 research. If none is found
within the spike week, this candidate **fails**. Do not wait for a reply
beyond the spike.

## 3. Urdu landscape check (1 day)

Check each for Urdu / Hindi transfer. Record licence + language even if
the answer is "no Urdu support".

| Candidate | Licence | Urdu? | Hindi transfer? | Notes |
|---|---|---|---|---|
| Fish Speech | — | — | — | — |
| VoxCPM2 (OpenBMB) | Apache-2.0 (verify) | — | — | — |
| Fun-CosyVoice 3.0 (0.5B) | Apache-2.0 (verify) | — | — | 1.5B not released; 3.5 API only |
| Piper `ur_PK` Fasih / Aegis | voice licence (check exact card) | fixed voice, no clone | — | Intelligibility baseline only |
| OpenF5-TTS | Apache-2.0 (verify) | — | — | — |

## 4. Test (only for candidates that pass 1–3)

Generate the same 10 Urdu test scripts (docs/BENCHMARK.md) in Mubashir's
voice (60-second proxy recording if the full 20-min Urdu recording is
not yet available). Score WER + listener naturalness vs ElevenLabs
v4 Turbo Urdu and v3 Urdu (whichever is actually available on the
test date).

| Script | Candidate WER | ElevenLabs WER | Blind win? |
|---|---|---|---|
| 1–10 | — | — | — |

## 5. Decision

- [ ] **PASS** — WER < 10% and blind-test win on ≥ 7/10 scripts vs the
  best ElevenLabs Urdu model. Urdu engine: ________ (name + version).
- [ ] **FAIL** — reason: ________. v1 ships English-only; Urdu stays
  "in research" in the README.

Decided by: ________ Date: ________
