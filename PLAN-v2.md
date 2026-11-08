# XploClone — PLAN v2 (revised)

**Repo:** `mubashiribstec/xploclone` (public, empty, `main`, created 2026-10-30)
**Owner:** Mubashir Ali
**Date:** 2026-10-30
**Status:** PLAN ONLY — no code, no branch, no push. This plan supersedes PLAN-v1. It incorporates AUDIT-v1 and the real-world comparison of 2026-10-30.
**Workflow:** plan → audit plan → compare plan to real world → implement → audit built project → fix issues.

**How to read this file:** §1 is the decision log — what changed from v1 and why. If you only read one section, read §1. The rest is the revised, implementable plan.

---

## 1. Decision log — what changed from PLAN-v1 and why

| # | Decision | Changed from v1 | Why (evidence) |
|---|---|---|---|
| D1 | **ElevenLabs Urdu benchmark is v4 Turbo AND v3, not v3 only** | v1 said Urdu was "only on v3" | ElevenLabs launched v4 / v4 Turbo on 28 Sep 2026, claiming 90+ languages including Urdu. The v1 claim was true on 21 Sep 2026 and outdated on 30 Oct 2026. The opening is now narrower: v4 *claims* Urdu, fluency varies, and Roman Urdu + Pakistani accent are still untested. Benchmark both v4 and v3 on the test date and record which was actually available. |
| D2 | **Pin Python 3.14.10, forbid Python 3.15 in v1** | v1 chose 3.14 but did not lock it | Python 3.15.2 is newest (25 Oct 2026), but PyTorch 2.14 `torch.compile` does not work on Python 3.15 yet and 3.15 wheels are only on download.pytorch.org, not PyPI. `requires-python = ">=3.14,<3.15"` in `pyproject.toml`. PyTorch 2.15 (GA 28 Oct 2026) is a separate spike, not an automatic upgrade. |
| D3 | **Pin PyTorch 2.14.1, CUDA 12.8 (`cu128`)** | v1 was vague ("2.14.x / 2.15 if verified") | 2.14.1 GA 30 Sep 2026 is the last version with a full, documented Python 3.14 story. Pin it, record the hash, evaluate 2.15 only after Chatterbox passes on 2.14.1. |
| D4 | **Pin FastAPI 0.162.0 as target, verify at build** | v1 cited 0.162.0 without noting the conflict | Official release notes say 0.162.0 (23 Oct 2026); pepy.tech said 0.143.1 (stale snapshot). Arch Linux agrees with 0.162.0. Implementer must run `pip index versions fastapi` at build and pin the exact version that passes tests. |
| D5 | **Forbid Node 20 and Next.js 15 in v1** | v1 did not state this as a rule | Node 20 is EOL (30 Apr 2026, no security fix in the 21 Oct 2026 release). Next.js 15 security support ended 21 Oct 2026 (extended to 31 Jan 2027 for critical fixes only). Next.js 16.4.1+ is the safe line after the 14 Oct 2026 RCE fix; `sharp` must be ≥0.35.5. |
| D6 | **Urdu demoted from "committed engine" to "gated 1-week research spike"** | v1 listed Kani-TTS Urdu / DeepSpeak-v1 as primary candidates | Kani-TTS Urdu is a community adaptation, not an official language; no verified checkpoint, licence, or model card was found. DeepSpeak-v1 has no public checkpoint found — CV/portfolio only. A plan cannot depend on a download that may not exist. |
| D7 | **English-only ship is an explicit, acceptable v1 outcome** | v1 mentioned it as Fallback C, but the success definition implied Urdu must ship | If no Urdu candidate passes Gate 2, v1 ships EN-US + EN-GB only, with Urdu listed as "in research". Shipping a Hindi voice or a generic Urdu voice as `mubashir-ur` is forbidden. |
| D8 | **Split latency into model TTFA and end-to-end turn; measure, do not claim** | v1 repeated vendor latency claims (75–470 ms conflict) | Chatterbox Turbo latency claims conflict across sources (75 ms vendor, ~200 ms guides, ~470 ms first chunk in one table). The only honest target is a measured p50/p95 on the prod GPU. |
| D9 | **Add OpenF5-TTS, Fish Speech, VoxCPM2 to the evaluation list** | v1 did not evaluate them for Urdu / English | OpenF5-TTS is Apache-2.0 (commercial-safe F5 retrain, quality unverified). VoxCPM2 (Apache-2.0) and Fish Speech are cited in Oct 2026 guides as safe open picks with cloning. Check licence + language for each; do not add without that check. |
| D10 | **Roman Urdu split: script is the gate, Roman is a stretch** | v1 implied a general Roman Urdu transliterator in v1 | Real-world Urdu agent guidance: send Urdu script when pronunciation matters; treat Roman Urdu as input to accept, not as the primary generation path. v1 gate is Urdu script; Roman Urdu is a 500-word dictionary stretch. |
| D11 | **Z640 / GTX 1660 Super is dev-only for TTS, not prod for calls** | v1 listed it as a dev host but did not make it a hard rule | 6 GB can run one TTS engine for dev, but cannot run STT + LLM + TTS together. Live-call prod requires a dedicated TTS GPU (≥12 GB) or cloud GPU. |
| D12 | **Add GPU-down fallback to Xplogent** | v1 had no failover | Single GPU is a single point of failure. If the TTS GPU is down, Xplogent must fall back to Cartesia / ElevenLabs, not go silent. This is a requirement for the Xplogent integration, not a nice-to-have. |
| D13 | **Add watermark-survival, backup/restore, and cost-sheet tasks** | v1 listed them as risks without tasks | Each is now a named task with an owner and a gate (see §10, §11). |

---

## 2. Product scope (revised)

### 2.1 What XploClone v2 is

Same as v1, with the corrections in §1:

A single-owner, self-hosted voice-cloning TTS service speaking **only in Mubashir Ali's voice**, in **three variants only** (or two, if Urdu fails Gate 2):

| Voice ID | Language / accent | Engine (v2) | Status |
|---|---|---|---|
| `mubashir-en-us` | English, US accent | Chatterbox Turbo (primary) | Committed |
| `mubashir-en-gb` | English, British accent | Chatterbox Turbo (primary) | Committed |
| `mubashir-ur` | Urdu script (+ Roman Urdu stretch) | **TBD — gated spike, see §4** | **Not committed** |

### 2.2 Non-goals (unchanged from v1, plus two additions)

- No generic multi-voice marketplace, no user-uploaded voices, no voice library.
- No other languages. The API rejects any language code other than `en-US`, `en-GB`, `ur`.
- No dubbing, voice changer, music, or sound effects.
- No public SaaS, billing, or pricing tiers in v1.
- No training a foundation model from scratch.
- No mobile app in v1.
- **Added:** No F5-TTS official weights, XTTS v2, Voxtral open weights, or Breeze TTS 2 in any shipped image — all are non-commercial. They may be used for benchmarking only, on a separate machine, never in the prod Docker image.
- **Added:** No claim that XploClone "beats ElevenLabs" in general. The claim is narrow and testable: on the owner's voice, in EN-US / EN-GB / Urdu, on the benchmark in §9, XploClone is at least as good in English and better in Urdu (or Urdu does not ship).

### 2.3 Success definition (revised)

v1 succeeds if **all** of these hold on the blind test (see §9):
1. English (US and GB) is rated at least as natural as ElevenLabs v4 Turbo by the owner + ≥2 native listeners per accent, **and**
2. **Either** Urdu passes Gate 2 against the best ElevenLabs Urdu model available on the test date (v4 Turbo if available, otherwise v3), **or** Urdu is explicitly deferred and v1 ships English-only with the reason recorded, **and**
3. Model TTFA p95 <200 ms on the prod GPU, and end-to-end call turn p95 <800 ms, **and**
4. Marginal cost per minute after the GPU is paid for is effectively $0, with the break-even vs ElevenLabs API ($0.034/min for v4 Turbo) calculated and recorded.

---

## 3. Architecture — 3-voice, 2-engine (revised)

Unchanged in shape from v1, with two revisions:

1. **The Urdu engine slot is empty until the spike passes.** The router must return `503 engine_unavailable` for `mubashir-ur` if the Urdu engine is not loaded, with a clear error — never silently fall back to an English engine or a Hindi voice.
2. **The English engine has a named fallback.** If Chatterbox Turbo fails Gate 1, the fallback order is: (a) Qwen3-TTS 1.7B Base, (b) OpenF5-TTS, (c) Chatterbox Multilingual V3. Each fallback is tested on the same blind test, not swapped on a hunch.

```
Client (web UI / Xplogent / xplosole)
        |
        v
  XploClone API (FastAPI 0.162.0, Python 3.14.10)
   - auth, rate limit, text normalisation
   - voice_id -> engine routing (hardcoded, 3 IDs only)
   - sentence chunking, streaming, watermark, logging
        |
   +----+----+
   |         |
   v         v
English    Urdu
Engine     Engine
Chatterbox [GATED — see §4]
Turbo 350M
   |         |
   v         v
 Audio: 24 kHz WAV (files) / 8 kHz μ-law, 20 ms frames (calls)
```

### 3.1 Pinned stack (v2 — verify at build, record exact pins in build log)

| Component | Pinned version (v2) | Source / note |
|---|---|---|
| Python | **3.14.10** (`>=3.14,<3.15`) | Newest 3.14 patch, 25 Oct 2026. Do not use 3.15.2 in v1 — see D2. |
| PyTorch | **2.14.1, CUDA 12.8 (`cu128`)** | GA 30 Sep 2026. Evaluate 2.15.0 only in a separate spike. |
| FastAPI | **0.162.0** (target; verify with `pip index versions fastapi`) | Official release notes, 23 Oct 2026. |
| Pydantic | v2, latest compatible with FastAPI 0.162.0 at build | Pin exact at build. |
| Uvicorn | latest `uvicorn[standard]` compatible at build | Pin exact at build. |
| Next.js | **16.4.3** (minimum 16.4.1) | Newest 23 Oct 2026; 16.4.1+ is the safe line after 14 Oct RCE fix. `sharp` ≥0.35.5. |
| Node.js | **26.12.1** (Active LTS from 28 Oct 2026) | Security release 21 Oct 2026. Fallback if tooling breaks: 24.22.1 (Maintenance LTS). Never Node 20. |
| React | Latest compatible with Next.js 16.4.3 at build | Pin exact at build. |
| Tailwind CSS | Latest v4 at build | Pin exact at build. |
| Docker Engine | **29.9.1** (host, verify at build) | Release audit 18 Oct 2026; containerd 2.4.2. |
| Docker Compose | v2 (bundled with Docker Engine 29.x) | Pin exact at build. |
| CUDA (container) | **12.8.0** base image `nvidia/cuda:12.8.0-runtime-ubuntu24.04` | Pin tag; do not float to `latest`. 12.9 exists — do not switch without a test. |
| Ubuntu (container) | **24.04 LTS** | Base for the CUDA image above. |
| PostgreSQL | **16** — only if needed in Phase 2 | Not required for v1 file generation. Do not add a DB to v1 unless metadata volume justifies it. |
| `uv` | Latest stable at build | Python dependency management; lockfile committed. |
| `ffmpeg` | System package in the API image | Audio resampling / transcoding. Pin via apt lock if available. |

**Rule:** "Latest" in this plan means "the pinned version above, verified at build time". If a newer patch is released between this plan and implementation, the implementer must test it and record the decision — not silently upgrade.

### 3.2 Components (revised)

Same as v1, with these changes:
- English engine: Chatterbox Turbo 350M, MIT, `pip install chatterbox-tts` — **pin the package version and the Hugging Face revision hash** at build. Do not float.
- English benchmark only: F5-TTS official weights (CC-BY-NC-4.0), Voxtral (CC-BY-NC-4.0), Breeze TTS 2 (non-commercial) — on a separate benchmark machine, never in the prod image.
- English commercial-safe alternatives to evaluate: Qwen3-TTS 1.7B Base (Apache-2.0, 3 s clone, 97 ms claimed first-packet, ~3.9 GB VRAM), OpenF5-TTS (Apache-2.0, quality unverified), Chatterbox Multilingual V3 500M (MIT, 23+ languages, no Urdu).
- Urdu engine: **TBD — gated spike (§4)**.
- Text normalisation: Python, custom module, with the Roman Urdu scope split in §4.3.
- Audio: `ffmpeg`, `soundfile`, `librosa`, `torchaudio`. Telephony: 8 kHz G.711 μ-law, 20 ms frames.
- Storage: local disk for v1; recordings encrypted, never in the public repo.
- Auth: API keys (hashed), single admin login. No OAuth in v1.
- Observability: JSON logs, `/health`, `/metrics`, per-request latency + chars + voice_id. No PII, no audio in logs.

---

## 4. Urdu engine — gated research spike (revised, replaces v1 §4)

### 4.1 The spike (Phase 1, parallel to English MVP, 1 week, time-boxed)

**Goal:** answer, with evidence, "can any licensed, downloadable model clone Mubashir's Urdu voice at acceptable quality, or not?"

**Spike tasks (in order, stop at the first pass):**
1. **Kani-TTS Urdu:** Find the exact Hugging Face repo for the Urdu variant (not just `niobures/Kani-TTS`, which has no model card). Record: repo URL, licence file, checkpoint hash, languages listed, and a 30-second Urdu sample. If no repo / licence / checkpoint can be found, the candidate **fails** — record why and move on.
2. **DeepSpeak-v1:** Contact the author / search for a public checkpoint. If no public checkpoint, licence, or download is found within the spike week, the candidate **fails** — record why and move on. Do not wait for a reply beyond the spike.
3. **Urdu landscape check (1 day):** Check Fish Speech, VoxCPM2 (Apache-2.0), and Fun-CosyVoice 3.0 (Apache-2.0, 0.5B, 9 languages, no Urdu) for Urdu / Hindi transfer. Record licence + language for each, even if the answer is "no Urdu support". Also check Piper `ur_PK` Fasih/Aegis licence from the exact voice card.
4. **Test:** For any candidate that passes (1)–(3), generate the same 10 Urdu test scripts (see §9) in Mubashir's voice (using a 60-second proxy recording if the full 20-min Urdu recording is not yet available) and score WER + listener naturalness vs ElevenLabs v4 Turbo Urdu and v3 Urdu.
5. **Decision:** Pass = WER <10% and blind-test win on ≥7/10 scripts vs the best ElevenLabs Urdu model. Fail = any candidate fails (1)–(4), or no candidate passes the test.

**Spike output:** a one-page `docs/URDU-SPIKE.md` with repo URLs, licences, checkpoint hashes, audio hashes, scores, and a clear PASS / FAIL. No spike output, no Urdu engine.

### 4.2 Fallbacks (revised order)

- **Fallback A — Fine-tune a permissive base on Urdu (Phase 2 research, not v1):** Fun-CosyVoice 3.0 (Apache-2.0, 0.5B) or Chatterbox Multilingual V3 (MIT) or Qwen3-TTS Base (Apache-2.0), LoRA-fine-tuned on Mubashir's 20-min Urdu + a commercially-clean Urdu corpus if one can be found. Note: CosyVoice 3 1.5B was not released as open weights, and CosyVoice 3.5 has no open weights (API only) — only Fun-CosyVoice3-0.5B-2512 is open. This fallback may fail; it is not a promise.
- **Fallback B — Piper `ur_PK` baseline:** Use only to test Urdu text normalisation and pronunciation. Never ship as `mubashir-ur`. Check the exact voice licence before any commercial use — most Piper voices are non-commercial.
- **Fallback C — Ship English-only:** If the spike fails, v1 ships EN-US + EN-GB only. Urdu is "in research" in the README. This is an acceptable, recorded outcome — not a failure of the project.

### 4.3 Urdu text handling (revised)

- **Gate (must pass):** Urdu script (اردو, RTL) → correct Urdu speech. Numbers (Western and Urdu digits), PKR prices, dates, times, and English loanwords (pronounced in English) must work.
- **Stretch (nice to have in v1):** Roman Urdu → correct Urdu speech, for the 500 most common Roman Urdu words in the recording scripts, via a dictionary + rules. Full Roman Urdu transliteration is Phase 2.
- **Out of v1:** General Roman Urdu transliteration, code-switching at scale, and Urdu dialect variation. Do not claim them.

---

## 5. Recording plan — 60 minutes total (revised)

Unchanged in amount (20 min per variant, 60 min total), with three additions:

### 5.1 Format (unchanged, non-negotiable)
WAV, 48 kHz, 16-bit, mono. Same mic, same room, same gain. Quiet, no echo. No clipping. Separate files per sentence preferred, with a CSV/JSON manifest.

### 5.2 Amount — with a caveat
Zero-shot needs only 5–10 s, but 20 min per variant is kept for reference choice, phoneme coverage, and a fine-tune pool. **Caveat (from audit):** the amount needed for a high-quality LoRA fine-tune is unverified — it may need 30–60 min per voice. If Gate 1 / Gate 2 fails on zero-shot and fine-tuning is tried, the owner may be asked to record more. Do not promise that 20 min is enough for fine-tuning.

### 5.3 Script content (revised — accent test set added)
Each variant's script must cover the v1 list (statements, questions, numbers, names, postcodes, recruitment phrases, product phrases, Urdu formal/informal) **plus**:
- **Accent minimal set (EN-US and EN-GB, same words, both variants):** "car, park, bath, dance, schedule, tomato, herb, water, better, about, laugh, grass, clerk, vase, leisure". This makes US vs GB measurable, not just "sounds British".
- **Urdu numbers and prices:** PKR amounts, phone numbers, dates in Urdu.

Scripts are a Phase 0 deliverable, reviewed by the owner before recording. They are not in this plan.

### 5.4 Consent and provenance (unchanged)
Spoken consent at the start of each session + written `CONSENT.md` (private copy only). Recordings never in the public repo. Recordings live in a private, encrypted store.

### 5.5 Proxy recording (new)
Phase 1 engine testing may start with a **60-second proxy recording** per variant (one clean minute, same format) so the team is not blocked waiting for the full 60 minutes. The benchmark gates still require the full recording — a proxy pass does not count as a gate pass.

---

## 6. API design (revised)

Same as v1, with these revisions:

### 6.1 REST — file generation
`POST /v1/tts` — unchanged, except:
- `voice_id` must be one of the 3 hardcoded IDs. Unknown ID → 400.
- If `voice_id` is `mubashir-ur` and the Urdu engine is not loaded → **503 `engine_unavailable`**, with a clear message. Never fall back silently.
- Max text: 5,000 characters per request (parity with ElevenLabs v3 limit; verify the v4 limit at benchmark time and record it — do not assume it is the same).
- `GET /v1/voices` — returns only the 3 voices, with `status: loaded | unavailable` per voice. No create/delete endpoints.

### 6.2 WebSocket — live calls (revised)
`WS /v1/tts/stream` — unchanged, except:
- **Chunking mode is a test item, not a fixed choice.** Test (a) streaming PCM chunks live to μ-law, and (b) batching by sentence boundary then transcoding. Pick the one that sounds better on a real phone line, even if it is ~100–200 ms slower on paper. Record the choice and why.
- Interrupt must flush the buffer and stop synthesis within <100 ms. This is a hard requirement.
- **GPU-down fallback:** If the TTS engine is unavailable mid-call, the WebSocket must send `{ "type": "error", "code": "engine_unavailable" }` immediately so Xplogent can fall back to Cartesia / ElevenLabs. It must not hang or go silent.

### 6.3 Text normalisation
Unchanged from v1, with the Roman Urdu scope split in §4.3.

### 6.4 Limits (revised)
- Max concurrent syntheses: **1 on a single GPU in v1**. Queue FIFO, max 10, timeout 30 s, else 503 with `Retry-After`.
- Rate limit: 60 req/min per API key (tunable).
- No audio stored by default. Admin `store_output=true` keeps output 7 days, then deletes.

---

## 7. Web UI (unchanged from v1)

Single-owner admin UI: Generate, Voices, History (last 50), API keys, Health. Next.js 16.4.3, Node 26.12.1, Tailwind. Browser never talks directly to the GPU server; API key never ships to the browser.

---

## 8. Infrastructure and deployment (revised)

### 8.1 Hosts (revised — hard rule added)

| Environment | Hardware | Purpose |
|---|---|---|
| Dev (owner's Z640) | HP Z640, GTX 1660 Super 6 GB VRAM, 16 GB+ RAM (32 GB recommended) | **Dev only.** Can run one English engine at a time. Cannot run F5-TTS comfortably, cannot run STT + LLM + TTS together. |
| Prod v1 (single GPU) | Cloud GPU or local server with **≥12 GB VRAM, dedicated to TTS** (RTX 4060 Ti 16 GB, RTX 5070, A10 / L4) | One concurrent call / generation. **Hard rule: TTS GPU is dedicated — do not share it with STT/LLM in v1.** |
| CI | GitHub Actions, CPU only | Lint, type-check, unit tests, Docker build (no GPU tests in CI) |

### 8.2 Docker (revised)
- Base: `nvidia/cuda:12.8.0-runtime-ubuntu24.04` (pin tag, verify at build).
- Python 3.14.10, `uv`, lockfile committed.
- Services: `api` (FastAPI + engines), `web` (Next.js). No `db` in v1 unless Phase 2 justifies it.
- GPU reservation: 1 device, `driver: nvidia`.
- Healthcheck on `/health`, restart `unless-stopped`, JSON logs to stdout.
- No secrets in image or git. `.env` (gitignored) or host secret store only.

### 8.3 Repo layout (planned)
Same as v1, plus `docs/URDU-SPIKE.md` and `docs/BENCHMARK.md` as required deliverables, and `docs/COST-SHEET.md` (see §11).

### 8.4 Backup and restore (new, Phase 5)
- Encrypted backup of: reference clips, speaker embeddings, LoRA adapters (if any), config, and API-key hashes (not plaintext keys).
- Tested restore: restore to a fresh host and generate a test clip. Record the restore time.
- If there is no tested restore, there is no backup — only a copy.

---

## 9. Testing and benchmark plan vs ElevenLabs (revised)

### 9.1 What is measured (revised)

| Metric | How | Target (v2) |
|---|---|---|
| Naturalness (MOS) | Blind, 1–5, owner + ≥2 native listeners per accent/language | EN ≥ ElevenLabs v4 Turbo; UR > best ElevenLabs Urdu available on test date |
| Accent correctness | Blind, ≥2 native US + ≥2 native GB listeners, same 5 sentences, rating "US / GB / neither / Pakistani" | US voice rated US by ≥3/4 listeners; GB voice rated GB by ≥3/4 listeners |
| Speaker similarity (SIM) | Human + embedding cosine | ≥0.80 cosine on held-out clips; human "sounds like Mubashir" |
| Intelligibility (WER) | Whisper transcription vs input text | EN <5%, UR <10% |
| Latency — model TTFA | Request → first audio chunk from engine, prod GPU, batch=1, 20 runs | **p50 <150 ms, p95 <200 ms** (measured, not claimed) |
| Latency — file | Request → complete file, ≤500 chars | First byte <500 ms, complete <2 s on prod GPU |
| Latency — end-to-end call | Caller ends speech → first word heard (STT+LLM+TTS+network) | **p95 <800 ms** on a real phone line |
| Cost per minute | GPU $/hour ÷ minutes/hour | Marginal ≈ $0 after GPU; break-even vs ElevenLabs API $0.034/min recorded |
| Watermark survival | Generate → transcode to 8 kHz μ-law → check PerTh detectable | Record pass/fail; if fail, record as limitation, do not claim compliance |
| Robustness | Long text, numbers, names, code-switching | No crashes, no truncated sentences without an error |

### 9.2 Blind-test protocol (revised)
1. Write 10 scripts per variant (30 total), as in v1, **plus** the accent minimal set (§5.3) for EN-US/EN-GB.
2. Generate each script with (a) XploClone, (b) **ElevenLabs v4 Turbo** (EN + UR if available), (c) **ElevenLabs v3** (UR, and EN as a quality reference), (d) ElevenLabs v4 (EN, quality mode).
3. On the test date, **record which ElevenLabs models actually list Urdu** (screenshot / copy of elevenlabs.io/docs/overview/models). Do not rely on a Sep 2026 article.
4. Randomise order, strip metadata, blind listeners.
5. Record results in `docs/BENCHMARK.md` with audio hashes, model versions, dates. Report the first take; note re-takes separately.

### 9.3 Gates (revised)

- **Gate 0 (Phase 0 end):** Urdu spike output exists (`docs/URDU-SPIKE.md`) with a clear PASS / FAIL. No spike, no Urdu work in Phase 2.
- **Gate 1 (Phase 1 end):** English zero-shot passes blind test vs ElevenLabs v4 Turbo on ≥7/10 scripts, and accent test passes (§9.1). If not, try Qwen3-TTS, then OpenF5-TTS, then fine-tune. If none passes, stop and re-plan.
- **Gate 2 (Phase 2 end):** Urdu candidate passes blind test vs the best ElevenLabs Urdu model on ≥7/10 scripts, WER <10%. If not, ship English-only and record the reason.
- **Gate 3 (Phase 3 end):** Live-call streaming passes on a real phone line with Xplogent, barge-in working, end-to-end turn p95 <800 ms on a 5-minute test call, and GPU-down fallback tested (kill the TTS service, confirm Xplogent falls back without silence).

---

## 10. Security, consent, watermarking, legal (revised)

- **Only Mubashir's voice.** No voice-upload endpoint in v1. Only the 3 hardcoded IDs, from his own recordings with written + spoken consent. This is the strongest control in the system.
- **Watermarking:** Preserve PerTh on every Chatterbox output. Do not strip watermarks. For Urdu, if the engine has no watermark, add a metadata marker and log the generation. **Test watermark survival through μ-law** (§9.1) — if it does not survive, record it as a limitation.
- **EU AI Act Art. 50:** In force 2 Aug 2026. XploClone is a new system, so **no grace period** — mark synthetic audio in a machine-readable format from day one, and Xplogent calls must disclose AI to the caller. The existing Xplogent greeting (AI disclosure + "This call is recorded") must be kept. Fines up to €15M or 3% of worldwide turnover are cited for Art. 50 breaches. This is not legal advice — confirm scope with qualified counsel before selling to EU/UK customers. Note: the UK is not in the EU, but the same disclosure is good practice and may be required by UK consumer / fraud rules — verify separately.
- **US / UK:** NO FAKES Act cleared US Senate committee June 2026, not law as of Oct 2026. Tennessee ELVIS Act is in force. The single-voice, own-voice design is the mitigation.
- **Data:** Recordings / embeddings are sensitive personal data. Encrypted at rest, access-logged, never in the public repo, never in a public bucket. Outputs deleted after 7 days unless explicitly kept. No audio in logs. Deletion on owner request within 7 days.
- **Abuse:** API keys per-client, rate-limited, revocable. Leaked key → revoke, do not blocklist.
- **No secrets in chat or git.** Benchmark ElevenLabs keys, GPU host credentials, and API keys live in `.env` / host secret store only.

---

## 11. Phased milestones (revised)

| Phase | Goal | Exit criteria |
|---|---|---|
| **Phase 0 — Spec, scripts, cost sheet (1 week)** | Recording scripts (EN-US, EN-GB, UR + Roman UR, incl. accent minimal set), consent template, benchmark scripts, repo skeleton, CI, **cost sheet** (`docs/COST-SHEET.md`: cloud GPU $/hour, expected min/month, break-even vs ElevenLabs API $0.034/min) | Scripts reviewed by owner; CI passing; cost sheet complete |
| **Phase 1 — English MVP + Urdu spike (2–3 weeks, parallel)** | Chatterbox Turbo in Docker on dev GPU; REST `/v1/tts`; web UI Generate page; blind test vs ElevenLabs; **Urdu spike (§4.1)** | Gate 0 (spike output) + Gate 1 passed; model TTFA p95 measured and recorded |
| **Phase 2 — Urdu API (2–4 weeks, gated)** | Only if Gate 0 passed: Urdu engine, Roman Urdu normaliser (500-word stretch), REST for `mubashir-ur` | Gate 2 passed, or English-only ship decision recorded |
| **Phase 3 — Live-call streaming (2–3 weeks)** | WebSocket `/v1/tts/stream`, 8 kHz μ-law, sentence chunking (test both chunking modes), interrupt, Xplogent integration on a test line, GPU-down fallback | Gate 3 passed on a real phone line |
| **Phase 4 — Fine-tune, if needed (3–4 weeks)** | LoRA per voice on the 20-min datasets, only if zero-shot is not close enough; re-benchmark | Fine-tuned beats zero-shot by ≥0.5 MOS, or revert to zero-shot. Owner may be asked to record more if 20 min is not enough — record the request, do not assume. |
| **Phase 5 — Hardening & handover (1–2 weeks)** | Rate limits, metrics, backup/restore (tested), docs, audit of built project, fix issues | Audit of built project complete; all critical issues fixed or recorded as known limitations |

Total v1 estimate: **8–13 weeks** from Phase 0 start, assuming recordings are delivered on time and Urdu passes the spike. If Urdu needs a from-scratch fine-tune, add 4–8 weeks and re-estimate at Gate 2. If Urdu fails the spike, v1 is **shorter** (English-only, ~6–9 weeks) — the spike saves time by failing fast.

---

## 12. Risks (revised — top risks first)

1. **Urdu engine may not exist as a usable, licensed checkpoint.** Mitigation: gated spike, English-only ship option. (Highest risk — see §4.)
2. **Accent separation may fail.** Mitigation: separate recordings, accent minimal set, native listener test. Re-record, do not blame the model for the input.
3. **Latency on the real GPU is unknown until measured.** Mitigation: split TTFA / end-to-end, measure p50/p95, test both chunking modes on a real phone line.
4. **6 GB VRAM is dev-only.** Mitigation: hard rule — prod TTS GPU is dedicated, ≥12 GB.
5. **Licence traps.** Mitigation: F5-TTS / XTTS v2 / Voxtral / Breeze are benchmark-only, never in prod. Pin licences in the build log.
6. **EU AI Act marking may not survive μ-law.** Mitigation: watermark-survival test, record pass/fail honestly.
7. **Single GPU = single point of failure.** Mitigation: GPU-down fallback to Cartesia / ElevenLabs in Xplogent.
8. **Recording quality is the ceiling.** Mitigation: format rules, proxy recording for testing, full recording required before gates.

---

## 13. Open questions for the owner (do not block Phase 0)

1. Where will the production GPU live — cloud (which provider?) or a local server?
2. Is the web UI hosted on Vercel (like xplosole) or on the same host as the API?
3. For Xplogent calls, which voice is the default — GB for UK, US for US, or configurable per campaign?
4. Should Urdu output be Urdu script by default, Roman Urdu by default, or chosen per request?

---

## Appendix — Sources checked 2026-10-30 (for the implementer to re-verify)

- Python: endoflife.date/python — 3.15.2 (25 Oct 2026), 3.14.10 (25 Oct 2026)
- FastAPI: fastapi.tiangolo.com/release-notes — 0.162.0 (23 Oct 2026)
- Next.js: guardlayer.io/blog/nextjs-latest-safe-version — 16.4.3 newest 23 Oct 2026, 16.4.1+ safe
- Node.js: nodejs.org schedule / digitalmatters.me — 26.12.1 / 24.22.1 / 22.23.4 (21 Oct 2026), Node 26 LTS 28 Oct 2026
- Docker: oday-bakkour.com — Docker Engine 29.9.1 (18 Oct 2026)
- PyTorch: dev-discuss.pytorch.org — 2.15.0 GA 28 Oct 2026, 2.14.1 GA 30 Sep 2026; Medium 12 Oct 2026 — `torch.compile` on Python 3.15
- Chatterbox: cartesia.ai/learn/open-source-tts, webdiga.com (checked 24 Oct 2026), pinggy.io — MIT, Turbo 350M, Multilingual V3 500M, 23+ langs
- F5-TTS / OpenF5-TTS: openspeech.dev (checked 20 Sep 2026) — MIT code / CC-BY-NC-4.0 weights; OpenF5-TTS Apache-2.0
- Qwen3-TTS: QwenLM / news.kloudihub.com — Apache-2.0, 0.6B/1.7B, 10 langs, no Urdu, Jan 2026
- Fun-CosyVoice 3.0: cosyvoice.org — Apache-2.0, 9 langs, no Urdu, 1.5B not released, 3.5 API only
- Kani-TTS: gadget.co.za, dxbnewsnetwork.com, huggingface.co/niobures/Kani-TTS — Apache-2.0 base, Urdu is community adaptation, no verified Urdu checkpoint
- DeepSpeak-v1: mahwiz.me/CV.pdf — portfolio description only, no public checkpoint found
- Piper Urdu: tts.ai/voices/piper, sonexlabs.com/blog/urdu-ai-voice-agent-pakistan (checked 24 Oct 2026) — ur_PK Fasih/Aegis, fixed voice, licence varies
- ElevenLabs v4: lapaasvoice.com, medium.com/@gsaidheeraj — v4/v4 Turbo 28 Sep 2026, 90+ langs incl. Urdu; bundledseo.com — Urdu only on v3 as of 21 Sep 2026 (outdated after v4)
- ElevenLabs pricing: convo360.ai / bundledseo.com — Sep 2026, Free $0/10k, Starter $6/30k, Creator $22/121k, Pro $99/600k; API v4 Turbo $0.04/1k chars
- EU AI Act Art. 50: regulation-ai.eu, genai.qa, blog.bluelupin.com — in force 2 Aug 2026, marking grace to 2 Dec 2026 for pre-existing systems, new systems from day one
- Telephony latency: dev.to/nexariza_ai, programminginsider.com — 8 kHz μ-law, 20 ms frames, TTS 100–200 ms, total turn <800 ms

*End of PLAN-v2. Next step (per owner workflow): implement PLAN-v2 on a branch, then audit the built project and fix issues. Do not implement from PLAN-v1.*
