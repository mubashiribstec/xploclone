# XploClone — AUDIT of PLAN-v1 + Real-World Comparison

**Date:** 2026-10-30
**Auditor:** self-audit of PLAN-v1, against web sources checked the same day
**Verdict:** PLAN-v1 is directionally sound (narrow scope, 2-engine router, single-owner voice, Chatterbox Turbo for English) but contains **one material factual error, three version traps, and one high-risk dependency presented as more solid than it is**. It must not be implemented as written. PLAN-v2 fixes all items below.

---

## A. Material correction — ElevenLabs Urdu is no longer "v3 only"

**PLAN-v1 claim:** "Urdu is rated clearly better than ElevenLabs v3 Urdu" / "ElevenLabs Urdu is weak: only on v3, not v4".

**What the real world says on 2026-10-30:**
- As of 21 Sep 2026, that claim was true: "Hindi is on every current model; Urdu and Bengali are only on Eleven v3" and "Urdu and Bengali are on Eleven v3 only, which means a 5,000-character limit" — BundledSEO, checked 21 Sep 2026 against elevenlabs.io/languages and elevenlabs.io/docs/overview/models.
- On **28 Sep 2026, ElevenLabs launched Eleven v4 and v4 Turbo**, claiming **90+ languages** (up from 70+ in v3). The v4 language list in launch coverage explicitly includes Urdu: "English, Hindi, Telugu, Tamil, Bengali, Kannada, Malayalam, Marathi, Urdu, Japanese, Spanish, Portuguese, and many more" — Medium / ElevenLabs v4 coverage, 29 Sep 2026. A second source: "The company's documentation lists languages ranging from English, Spanish and French to Hindi, Bengali, Gujarati, Marathi, Tamil, Telugu, Urdu, Japanese, Mandarin, Korean and Cantonese" for v4 — LapaasVoice, 6 Oct 2026.

**Impact:** The competitive opening has narrowed. It is no longer "ElevenLabs has no modern Urdu model". It is now: "ElevenLabs *claims* Urdu on v4, but fluency varies by language, and v4 Urdu quality on a real Pakistani voice, with Roman Urdu input, is untested."

**Fix for PLAN-v2:**
- Change the Urdu benchmark comparator from "ElevenLabs v3 Urdu" to **"ElevenLabs v4 Turbo Urdu AND v3 Urdu, whichever is actually available on the owner's account on the test date"**. Test both, report both.
- Change the success claim from "better than v3" to "better than the best ElevenLabs Urdu model available at test time, on the same script, judged by native Urdu listeners".
- Keep the *real* differentiators, which survive the correction: (1) Roman Urdu input, (2) a Pakistani-accented Urdu voice that is Mubashir's own, not a generic Hindi-recorded voice, (3) zero per-minute cost, (4) no 5,000-char v3 limit if v4 is used — but verify the v4 limit at test time, do not assume it.
- Add a pre-benchmark task: on the test date, check elevenlabs.io/docs/overview/models for the Urdu row and screenshot/record it. Do not rely on a Sep 2026 article.

**Severity: HIGH — factual, affects the core value proposition.**

---

## B. Version traps — "latest" is not "safest"

### B1. Python 3.15 vs 3.14 — PLAN-v1 chose 3.14, correctly, but the reasoning must be locked

- Python 3.15.2 was released 25 Oct 2026 and is the newest release; 3.14.10 was also released 25 Oct 2026 — endoflife.date, 27 Oct 2026.
- PyTorch 2.14: "Python 3.15 support is eager mode only. PyTorch 2.14 has wheels for Python 3.15, including the free-threaded build. But `torch.compile` doesn't work on Python 3.15 yet. It raises an error instead of silently running slower. If you rely on `torch.compile`, stay on Python 3.14 or earlier for now. Python 3.15 wheels are also available only from download.pytorch.org, not from PyPI." — Medium, 12 Oct 2026.
- PyTorch 2.15.0 GA was announced 28 Oct 2026 (PyTorch dev-discuss). Whether 2.15 fixes `torch.compile` on Python 3.15 was **not verified** in v1 research.

**Audit finding:** PLAN-v1's choice of Python 3.14.10 is correct, but fragile. If the implementer "upgrades to latest" (3.15.2) without checking, the build will break or silently lose `torch.compile`.

**Fix for PLAN-v2:** Pin **Python 3.14.10** explicitly, with the reason in the plan and in `pyproject.toml` (`requires-python = ">=3.14,<3.15"`). Add a build-time check: if PyTorch 2.15 is verified to support `torch.compile` on 3.15, that is a separate, recorded decision — not an automatic upgrade. Do not use Python 3.15 in v1.

### B2. FastAPI — sources conflict by a wide margin

- Official release notes: **0.162.0 (23 Oct 2026)** — fastapi.tiangolo.com/release-notes.
- PyPI stats page (pepy.tech, crawled 2 hours before audit): "The latest version is 0.143.1, released Oct 14, 2026."
- Arch Linux: `python-fastapi 0.162.0-1`, build date 24 Oct 2026.

**Audit finding:** The 0.143.1 figure is stale / a different index snapshot. The official release notes and Arch both agree on 0.162.0. PLAN-v1 was right to use 0.162.0, but the plan must tell the implementer to verify with `pip index versions fastapi` at build time and to pin the exact version that passes tests, not to trust any single secondary source.

**Fix for PLAN-v2:** Keep 0.162.0 as the *target*, add "verify at build, pin exact, record the pinned version in the build log".

### B3. PyTorch version — PLAN-v1 is vague

PLAN-v1 says "PyTorch 2.14.x / 2.15 if verified" in one place and "PyTorch 2.14 (cu128)" in another. That is not a pin.

**Fix for PLAN-v2:** Pin **torch 2.14.1, CUDA 12.8 (`cu128`)** as the v1 baseline, because 2.14.1 GA was 30 Sep 2026 and is the last version with a full, documented 3.14 story. Evaluate PyTorch 2.15.0 (GA 28 Oct 2026) only in a separate spike, after Chatterbox is proven on 2.14.1. Record the decision.

### B4. Next.js / Node — PLAN-v1 is correct, but the security context must be explicit

- Next.js 16.4.3 is the newest release as of 23 Oct 2026; 16.4.1+ is the safe line after the 14 Oct 2026 out-of-band RCE fix (two Critical RCEs + one High DoS, fixed in 16.4.1 and 15.5.28). `sharp` must be 0.35.5+.
- Node.js 26.12.1 / 24.22.1 / 22.23.4 security release 21 Oct 2026; Node 26 becomes Active LTS 28 Oct 2026; Node 24 entered Maintenance LTS 20 Oct 2026; Node 20 is EOL (30 Apr 2026) and gets no fix.
- Next.js 16 needs Node.js 20.9+.

**Audit finding:** No error, but PLAN-v1 must forbid Node 20 and Next.js 15 in v1. Add that as a hard rule in PLAN-v2.

### B5. Docker — PLAN-v1 cites 29.9.1, which is correct but thin

Docker Engine 29.9.1 was the current audit version on 18 Oct 2026 (containerd 2.4.2, three vulnerabilities fixed). PLAN-v2 should pin the Docker Engine version on the host at build time and record it, not just cite the audit.

---

## C. Latency — conflicting claims, none measured on the owner's hardware

PLAN-v1 repeats vendor / guide claims without reconciling them:

| Source | Chatterbox Turbo latency claim |
|---|---|
| Resemble / vendor material via RiseWithVishwas | ~75 ms, up to 6× real-time |
| Pinggy / BentoML guides | ~200 ms latency, Turbo at 75 ms |
| ocdevel table | ~470 ms first chunk, ~2× real-time, ~6 GB VRAM |
| Forasoft / general guides | 150–200 ms |

**Audit finding:** These cannot all be true on the same hardware. The difference is likely: model-only TTFA vs end-to-end HTTP TTFA, GPU model, batch size, and whether the first chunk is a full sentence or a partial frame. PLAN-v1's target "<200 ms first audio for calls" is a *goal*, not a measured fact.

**Fix for PLAN-v2:**
- Split the target into two numbers: (a) **model TTFA** (request to first audio chunk from the engine, on the prod GPU, batch=1), target <200 ms; (b) **end-to-end turn latency** (caller ends speech → first word heard, including STT + LLM + TTS + network), target <800 ms, with the TTS budget explicitly 100–200 ms inside that total — the standard voice-agent budget cited in Oct 2026 guides (STT 300 ms + LLM 200–400 ms + TTS 100–200 ms + network 50–100 ms).
- Add a latency-measurement task in Phase 1: measure TTFA on the *actual* prod GPU with a fixed script, 20 runs, report p50/p95. If p95 >200 ms, the plan must say so and either change GPU or change the target — not hide it.
- Note the telephony chunking trap found in real-world reports: streaming raw PCM chunks and compressing live to μ-law can create audible chunking at codec boundaries; some builders batch by sentence boundary instead, adding ~100–200 ms per sentence but playing smoothly. PLAN-v2 must test both modes on a real phone line and pick the one that sounds better, even if it is slower on paper.

**Severity: MEDIUM — affects the live-call promise.**

---

## D. Urdu — the highest-risk dependency is presented as more solid than it is

### D1. Kani-TTS Urdu is a community adaptation, not an official language

- Kani-TTS base (NineNineSix, Apache-2.0) officially supports: English, German, Korean, Arabic, Chinese, Spanish, Kyrgyz, Japanese (v1, 8 languages) / English, Spanish, Kyrgyz (v2, 3 languages in the v2 announcement).
- Urdu is **not** in either official list. Multiple sources say the same thing: "External teams have successfully adapted the model for languages such as Vietnamese, Urdu, Creole, and Hausa" and "Community contributors independently trained new language models, including Urdu and Vietnamese, using the open architecture. In several cases, these community-driven extensions achieved production-level quality." — CES 2026 coverage / Gadget, Feb 2026.
- The Hugging Face model `niobures/Kani-TTS` (0.4B params) has **no model card** in the search result. No licence, no Urdu checkpoint link, no WER / MOS was verified.

**Audit finding:** PLAN-v1 lists Kani-TTS-400M-UR as "primary candidate" without a verified checkpoint, licence, or benchmark. That is a plan built on a lead, not a dependency.

**Fix for PLAN-v2:** Demote Kani-TTS Urdu to "Candidate 1 — research spike, 1 week, go/no-go gate". The spike must produce: exact HF repo URL, licence file, checkpoint hash, a 30-second Urdu sample in Mubashir's voice (or a close proxy if his recording is not yet available), and a WER / listener score. If any of those cannot be produced, the candidate fails the spike.

### D2. DeepSpeak-v1 — no public checkpoint was found

- DeepSpeak-v1 is described in Muhammad Mahwiz Khalil's CV/portfolio: "Trained an Urdu text-to-speech model from scratch using rectified flow matching with a Qwen3.5-0.8B text backbone and reference-audio speaker conditioning, supporting voice cloning from 3–15 second clips" and "Built production-ready Speech-to-Text and Text-to-Speech systems for Urdu … including the Aegis, Cadenza, DeepSpeak-v1, and Kani-TTS Urdu TTS models".
- No Hugging Face model card, GitHub repo, licence, or download link for DeepSpeak-v1 was found in v1 research.

**Audit finding:** Treat DeepSpeak-v1 as an **unverified lead to contact / chase**, not as a candidate that can be downloaded. PLAN-v2 must not list it as "primary candidate" alongside Kani-TTS. If the author cannot be reached or no checkpoint is published, it drops out with no effect on the schedule.

### D3. Piper Urdu — exists, but is not a clone and is not clearly commercial

- Piper lists Urdu among 35+ languages, with voices `ur_PK` Fasih (male) and Aegis (female) — TTS.ai / Piper voices, and Sonex Labs (checked 24 Oct 2026): "Piper (offline, open source) — Yes: ur_PK fasih".
- A Home Assistant thread from Jan 2026 says the opposite: "Piper: I can't find any official Urdu voice/model for it" and "Coqui XTTS-v2: official language list doesn't include Urdu". The contradiction is likely a timing / repo issue (ur_PK was added later, or is in `rhasspy/piper-voices` on Hugging Face but not in the main Piper docs).
- Piper engine is MIT, but "each voice carries the license of the recordings it was trained on, and most Piper voices were trained on or fine-tuned from recordings licensed for non-commercial use" — TTS.ai.

**Audit finding:** Piper Urdu is a useful *intelligibility baseline* for text normalisation, not a voice clone, and its commercial licence for Fasih/Aegis must be checked from the exact voice card before any commercial use. PLAN-v1 was right to put it as Fallback A, but must add the licence check as a task.

### D4. What PLAN-v1 missed — other commercial-safe models that could help Urdu

PLAN-v1 did not evaluate:
- **Fish Speech / Fish Audio** — multilingual, cloning, but licence / Urdu support not checked in v1.
- **VoxCPM2 (OpenBMB, Apache-2.0)** — cited in Oct 2026 guides as a safe open pick with cloning, alongside Chatterbox. Not evaluated for Urdu.
- **Fun-CosyVoice 3.0 (Apache-2.0, 0.5B, 9 languages)** — PLAN-v1 lists it as a fine-tune base, but did not note that the 1.5B CosyVoice 3 paper model was **not** released as open weights, and CosyVoice 3.5 has **no open weights published** (API only). Only Fun-CosyVoice3-0.5B-2512 is open.
- **Qwen3-TTS** — correctly noted as 10 languages, no Urdu, Apache-2.0, 0.6B ~3.9 GB VRAM / 1.7B ~3.9 GB VRAM in one benchmark (conflicting VRAM figures in sources — 0.6B is ~2.5 GB weights, 1.7B ~4.5 GB weights; VRAM depends on precision and batch).

**Fix for PLAN-v2:** Add a 1-day "Urdu landscape" spike task that checks Fish Speech, VoxCPM2, and Fun-CosyVoice 3.0 for Urdu / Hindi transfer, and records the result even if it is "no Urdu support". Do not add a model to the plan without a licence + language check.

### D5. Roman Urdu — PLAN-v1 underestimates the work

PLAN-v1 says "deterministic transliteration table + exception dictionary". Real-world Urdu voice-agent guidance (Sonex Labs, Oct 2026) says the opposite approach is safer: "Send Urdu script to the voice whenever pronunciation matters, and treat Roman Urdu as something to accept from customers rather than something to generate. Let the language model write its replies in Urdu script."

**Audit finding:** Roman Urdu *generation* (TTS reading Roman Urdu text aloud in correct Urdu) is harder than Roman Urdu *understanding* (ASR / LLM reading it). PLAN-v1 must split them:
- v1 gate: Urdu script → correct Urdu speech.
- v1 stretch: Roman Urdu → correct Urdu speech, with a dictionary for the 500 most common Roman Urdu words in the recording scripts. Full Roman Urdu transliteration is Phase 2, not v1.

**Severity for Urdu overall: HIGH — this is the single biggest risk to v1. The plan must be honest that Urdu may ship late or not at all in v1.**

---

## E. Accent — PLAN-v1 is correct, but incomplete

PLAN-v1 correctly identifies the accent trap and fixes it with separate recordings. Two gaps remain:

1. **No accent test in the plan.** The plan says "if the GB recording still sounds American to native GB listeners, re-record" — but does not say *who* the listeners are, *how many*, or *what script* they hear. PLAN-v2 must add: ≥2 native GB listeners and ≥2 native US listeners, blind, same 5 sentences, rating "US / GB / neither / Pakistani" — not just "natural".
2. **No phoneme coverage check.** US vs GB differs in specific sounds (rhotic /r/, "bath" vowel, "schedule", "tomato", etc.). The recording scripts must include a minimal accent test set (e.g. "car, park, bath, dance, schedule, tomato, herb, water, better, about") in both variants, so the difference is measurable, not just "sounds British".
3. **OpenVoice V2 is correctly rejected for real-time, but its accent-control idea should be kept as a research note** — if separate recordings fail, a future accent-conversion experiment (fine-tune on GB-only data, as in the accent-conversion literature) is a Phase 4 option, not a v1 fix.

---

## F. Hardware — 6 GB is marginal, and PLAN-v1 understates it

- Chatterbox Turbo: ~4–6 GB VRAM (one guide), ~6 GB in another table. Qwen3-TTS 0.6B: ~3.9 GB VRAM in an RTX 3090 benchmark; 1.7B: ~3.9 GB as well in that benchmark (likely bf16, batch=1). F5-TTS: needs ~8–12 GB.
- The Z640 + GTX 1660 Super (6 GB) can run **one** English engine at a time for development. It cannot run STT (Whisper large-v3-turbo int8) + LLM (8B) + TTS together on the same card — the owner's own Xplogent guidance already says this: "cannot run an 8B LLM and large-v3-turbo Whisper both fully on the 6GB GPU at once".
- For Xplogent live calls, the TTS GPU is **separate** from the STT/LLM GPU unless a larger card is bought. PLAN-v1 says this in the infra table but does not make it a hard rule.

**Fix for PLAN-v2:** Add a hard rule — "v1 live-call deployment requires a dedicated GPU for TTS, or a cloud GPU with ≥12 GB VRAM. The Z640 1660 Super is dev-only for TTS, not prod for calls." Add a cost table: cloud A10 / L4 hourly rate (to be filled at implementation from the chosen provider — do not guess a price in the plan).

---

## G. Single points of failure and missing pieces

| Gap | Severity | Fix in PLAN-v2 |
|---|---|---|
| Single GPU, no HA, no failover | Medium | Record as accepted risk in v1; add a "GPU down = TTS down, Xplogent falls back to Cartesia/ElevenLabs" fallback in the Xplogent integration spec |
| No backup/restore for voice embeddings / adapters | Medium | Add a backup task: encrypted backup of reference clips + embeddings + adapters, tested restore, in Phase 5 |
| No model version pinning for Chatterbox (`pip install chatterbox-tts` floats) | Medium | Pin package version + Hugging Face revision hash at build; record both in the build log |
| No cost model for prod GPU | Medium | Add a cost sheet task in Phase 0: cloud GPU $/hour, expected minutes/month, break-even vs ElevenLabs API $0.034/min |
| No data-retention / deletion procedure for recordings | Low | Add: recordings encrypted, access log, deletion on owner request within 7 days |
| No test for watermark survival through μ-law | Medium | Add to benchmark: generate, transcode to 8 kHz μ-law, check PerTh watermark still detectable; if not, record as limitation |
| No handling of long-form / very long text (chunking, prosody across chunks) | Low | Add: chunk at sentence boundaries, keep a 1-sentence overlap for prosody, test on a 500-word script |
| No "what if the owner is unavailable to record" plan | Low | Add: Phase 1 can start with a 60-second proxy recording for engine testing; the real 60-min recording is still required before the benchmark gate |
| ElevenLabs pricing in PLAN-v1 mixes app and API prices | Low | Clarify: app Starter $6/30 min (~$0.20/min), Creator $22/121 min (~$0.18/min); API v4 Turbo $0.04/1k chars (~$0.034/min). The break-even math must use the API price for Xplogent, not the app price. |

---

## H. Real-world comparison — summary table

| PLAN-v1 assumption | Real world (30 Oct 2026) | Verdict |
|---|---|---|
| ElevenLabs Urdu only on v3 | v4 launched 28 Sep 2026, claims 90+ langs incl. Urdu | **OUTDATED — correct in PLAN-v2** |
| Python 3.15 is latest, use 3.14 | 3.15.2 is latest, but `torch.compile` broken on 3.15 in PyTorch 2.14 | **PLAN-v1 choice correct, reasoning must be locked** |
| FastAPI 0.162.0 | Official notes 0.162.0 (23 Oct); pepy says 0.143.1 (stale) | **Correct, verify at build** |
| Next.js 16.4.3, Node 26.12.1 | 16.4.3 newest 23 Oct; Node 26 LTS 28 Oct, 26.12.1 fixed 21 Oct | **Correct** |
| Chatterbox Turbo MIT, 5 s clone, <150 ms | MIT confirmed; latency claims 75–470 ms conflict | **Licence correct, latency unverified** |
| F5-TTS CC-BY-NC, test only | Confirmed; OpenF5-TTS Apache-2.0 is the commercial-safe retrain | **Correct, add OpenF5 spike** |
| Qwen3-TTS Apache, 10 langs, no Urdu | Confirmed, Jan 2026, 0.6B/1.7B | **Correct** |
| CosyVoice no Urdu | Fun-CosyVoice 3.0 Apache, 9 langs, no Urdu; 1.5B not released, 3.5 API only | **Correct, add the 1.5B/3.5 caveat** |
| Kani-TTS Urdu is a primary candidate | Community adaptation only, no verified checkpoint / licence / model card | **OVERSTATED — demote to spike** |
| DeepSpeak-v1 is a primary candidate | CV/portfolio only, no public checkpoint found | **OVERSTATED — demote to lead** |
| Piper Urdu is a fallback | ur_PK Fasih/Aegis exist, fixed voice, licence varies, one source says no official Urdu voice (Jan 2026, likely outdated) | **Correct as baseline, add licence check** |
| 20 min per variant is enough | Zero-shot needs 5–10 s; LoRA fine-tune amount is unverified, may need 30–60 min for high quality | **UNVERIFIED — test, do not assume** |
| 6 GB GPU can do live calls | Can run one TTS engine for dev; cannot run STT+LLM+TTS together | **OVERSTATED for prod — dev-only** |
| EU AI Act marking from day one for new systems | Confirmed: Art. 50 in force 2 Aug 2026, grace to 2 Dec 2026 only for pre-existing systems | **Correct** |

---

## I. Audit decision

**Do not implement PLAN-v1 as written.**

Implement PLAN-v2, which must:
1. Correct the ElevenLabs v4 Urdu claim and benchmark.
2. Pin Python 3.14.10 / PyTorch 2.14.1 cu128 / FastAPI 0.162.0 (verify at build) / Next.js 16.4.3 / Node 26.12.1.
3. Demote Urdu to a gated 1-week research spike with a go/no-go gate, and add an English-only ship option.
4. Split latency targets into model TTFA and end-to-end turn, and measure on the real GPU.
5. Add accent listener tests, Roman Urdu scope split, watermark-survival test, GPU-down fallback, backup/restore, and cost sheet.
6. Add OpenF5-TTS, Fish Speech, and VoxCPM2 to the evaluation list (check, do not assume).

*End of AUDIT-v1.*
