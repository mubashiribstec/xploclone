# XploClone — PLAN v1

**Repo:** `mubashiribstec/xploclone` (public, empty, `main`, created 2026-10-30)
**Owner:** Mubashir Ali
**Date:** 2026-10-30
**Status:** PLAN ONLY — no code, no branch, no push. This is the v1 plan to be audited, compared to the real world, then revised into PLAN-v2.
**Workflow set by owner:** plan → audit plan → compare plan to real world → implement → audit built project → fix issues. Use latest coding and versions, full potential.

---

## 0. Sources and verification rule

Every version and licence claim below was checked by web search on 2026-10-30. Where sources conflict, the conflict is noted in-line and must be re-verified at implementation time by reading the upstream release page / model card — never by trusting this plan alone.

Standing rule (owner, 2026-10-26): use full power, check work twice, never decide on guessing. Anything unverified is marked **UNVERIFIED**.

Key sources used for v1:
- Python 3.15.2 (25 Oct 2026) is the newest release; 3.14.10 also released 25 Oct 2026 — endoflife.date / python.org
- FastAPI 0.162.0 (23 Oct 2026) in official release notes — fastapi.tiangolo.com/release-notes
- Next.js 16.4.3 newest as of 23 Oct 2026; 16.4.1+ is the safe line after the 14 Oct 2026 RCE fix — guardlayer.io / Next.js advisories
- Node.js 26.12.1 / 24.22.1 / 22.23.4 security release 21 Oct 2026; Node 26 becomes Active LTS 28 Oct 2026; Node 24 in Maintenance LTS from 20 Oct 2026 — nodejs.org schedule
- Docker Engine 29.9.1 (Oct 2026) — release audit 18 Oct 2026
- PyTorch 2.15.0 GA 28 Oct 2026; PyTorch 2.14.1 GA 30 Sep 2026; PyTorch 2.14 `torch.compile` does NOT work on Python 3.15 — PyTorch dev-discuss / Medium 12 Oct 2026
- Chatterbox family: Turbo 350M, Multilingual V3 500M, Nano 110M; MIT; Turbo English-only; Multilingual 23+ languages — Resemble AI / Cartesia / webdiga, checked 24 Oct 2026
- F5-TTS: MIT code, CC-BY-NC-4.0 weights; OpenF5-TTS is Apache-2.0 — openspeech.dev (checked 20 Sep 2026)
- Qwen3-TTS: Apache-2.0, 0.6B / 1.7B, 10 languages, no Urdu — QwenLM, Jan 2026
- Fun-CosyVoice 3.0: Apache-2.0, 9 languages, no Urdu; 1.5B paper model not released — cosyvoice.org, Oct 2026
- ElevenLabs v4 / v4 Turbo launched 28 Sep 2026, 90+ languages — ElevenLabs launch coverage
- ElevenLabs pricing Sep 2026: Free $0 / 10k credits, Starter $6 / 30k, Creator $22 / 121k, Pro $99 / 600k — elevenlabs.io/pricing, checked 17–21 Sep 2026
- EU AI Act Art. 50 in force 2 Aug 2026; marking grace to 2 Dec 2026 for pre-existing systems; new systems must mark from day one — Regulation (EU) 2024/1689 / Digital Omnibus 2026/1744
- Telephony: 8 kHz G.711 μ-law, 20 ms frames, TTS first-byte budget 100–200 ms, total turn budget <800 ms for natural conversation — voice-agent architecture guides, Oct 2026

---

## 1. Product scope

### 1.1 What XploClone v1 is

A single-owner, self-hosted voice-cloning TTS service that speaks **only in Mubashir Ali's voice**, in **three variants only**:

| Voice ID | Language / accent | Use |
|---|---|---|
| `mubashir-en-us` | English, US accent | US products, xplosole videos for US audience |
| `mubashir-en-gb` | English, British accent | UK recruitment calls via Xplogent, UK products |
| `mubashir-ur` | Urdu (Urdu script + Roman Urdu input) | Pakistan / Urdu-speaking users, Urdu videos and calls |

The service is an internal engine first, a product second. It exists to remove the per-minute ElevenLabs bill from Mubashir's own products and to give him a voice no vendor can change, reprice, or take away.

### 1.2 Non-goals for v1 (explicitly out)

- No generic multi-voice marketplace. No user-uploaded voices. No voice library, no voice design from text prompts.
- No other languages. No Hindi, Arabic, French, etc., even if the base model supports them. The API must reject any other language code.
- No dubbing, no voice changer / speech-to-speech, no music, no sound effects.
- No public SaaS signup, no billing, no pricing tiers in v1. Single owner, single API key set.
- No training a foundation TTS model from scratch. v1 uses open pre-trained models + zero-shot cloning, then LoRA / fine-tuning only if the benchmark proves it is needed.
- No mobile app in v1. Web UI + API + Xplogent integration only.
- No replacing Xplogent's LLM or STT in v1. XploClone replaces only the TTS stage.

### 1.3 Success definition for v1

v1 succeeds if, on a blind test with the same scripts:
1. English (US and GB) is rated at least as natural as ElevenLabs Flash / v4 Turbo by the owner and at least 2 native listeners per accent, **and**
2. Urdu is rated clearly better than ElevenLabs v3 Urdu on the same script (the stated ElevenLabs weak spot), **and**
3. Live-call first-audio is <200 ms from TTS request on the production GPU, **and**
4. Marginal cost per minute after the GPU is paid for is effectively $0 (no per-character vendor bill).

If (2) cannot be met, v1 ships English-only and Urdu is a gated Phase 2 — it is not faked with a Hindi voice or a generic Urdu voice. See §9.

---

## 2. Architecture — 3-voice, 2-engine

### 2.1 Why two engines

No single permissively-licensed open model in Oct 2026 does both high-quality English cloning **and** Urdu cloning well.

- The best commercial-safe English cloners (Chatterbox, Qwen3-TTS) do not list Urdu.
- The Urdu-capable models found are small, community, or fixed-voice — not proven cloners at ElevenLabs quality.

So v1 is a **router + two engines behind one API**:

```
Client (web UI / Xplogent / xplosole)
        |
        v
  XploClone API (FastAPI)
   - auth, rate limit, text normalisation
   - voice_id -> engine routing (hardcoded map, 3 IDs only)
   - sentence chunking, streaming, watermark, logging
        |
   +----+----+
   |         |
   v         v
English    Urdu
Engine     Engine
Chatterbox Qwen3 / Kani /
Turbo      DeepSpeak (see §4)
   |         |
   v         v
 Audio out: 24 kHz WAV (files) / 8 kHz μ-law (calls)
```

The caller never picks an engine. It picks a `voice_id`. The router is the only place that knows which engine serves which voice. This lets the Urdu engine be swapped without changing any client.

### 2.2 Components

| Component | Technology (v1) | Notes |
|---|---|---|
| TTS API server | Python 3.14.10, FastAPI 0.162.0, Uvicorn, Pydantic v2 | Async, OpenAPI at `/docs`, WebSocket for streaming |
| English engine | Chatterbox Turbo 350M, MIT | Zero-shot, 5 s reference, ~75–150 ms claimed TTFA (see audit) |
| English benchmark only | F5-TTS official weights, CC-BY-NC-4.0 | Test/benchmark only. Never shipped, never in prod image |
| English commercial-safe alt | OpenF5-TTS, Apache-2.0 | Evaluate in Phase 1 spike; quality UNVERIFIED |
| Urdu engine (primary candidate) | Kani-TTS 2 / Kani-TTS-400M-UR community Urdu, or DeepSpeak-v1 | Both UNVERIFIED — see §4 and audit |
| Urdu fallback A | Piper `ur_PK` Fasih / Aegis (fixed voice, no clone) | Intelligibility baseline only, not Mubashir's voice |
| Urdu fallback B | Fine-tune a permissive base (Chatterbox Multilingual / Fun-CosyVoice 3.0 / Qwen3-TTS) on Urdu data | Transfer learning; high risk, Phase 2 only |
| Web UI | Next.js 16.4.3, Node.js 26.12.1, React, Tailwind | Single-owner admin UI; hosted on Vercel or same host as API — decision at build |
| Text normalisation | Python, custom module | Numbers, dates, abbreviations, Roman Urdu → Urdu phonemes, English loanwords in Urdu |
| Audio processing | `ffmpeg`, `soundfile`, `librosa`, `torchaudio` | Resample 24 kHz → 8 kHz μ-law for telephony; loudness normalisation |
| Storage | Local disk for v1 (recordings, embeddings, outputs); PostgreSQL 16 for metadata in Phase 2 if needed | No cloud bucket in v1. Recordings are the owner's voice — treat as sensitive |
| Auth | API keys (hashed, per-client), single admin login | No OAuth, no multi-user in v1 |
| Infra | Docker + Docker Compose, Ubuntu 24.04 LTS base, NVIDIA Container Toolkit, CUDA 12.8 | One GPU host; `docker compose up` is the deploy |
| Observability | Structured JSON logs, `/health`, `/metrics`, per-request latency + chars + voice_id | No PII in logs; no audio stored by default |

### 2.3 Voice identity model

- Each voice is a **reference embedding + reference audio clip(s)**, not a full model copy.
- Zero-shot path: the engine loads the reference clip at request time (or caches its embedding in GPU memory at startup) and synthesises new text in that voice.
- Fine-tuned path (Phase 3 only): a LoRA adapter per voice, stored as `adapters/mubashir-en-us/`, etc., loaded on top of the base model. The base model licence still governs the adapter's use — an adapter on a CC-BY-NC base does not make it commercial.
- Voice IDs are hardcoded in config. There is **no API endpoint to create a new voice** in v1. Adding a voice is a code + config change, reviewed by the owner.

---

## 3. English engine choice

### 3.1 Decision (v1)

**Primary: Chatterbox Turbo (Resemble AI), 350M parameters, MIT licence.**

Reasons:
- MIT licence, code and weights — commercial use OK, no weight-licence trap.
- Zero-shot cloning from ~5 seconds of reference audio.
- Built for low latency: distilled 1-step decoder (from 10 steps), claimed up to 6× faster than real-time, ~75 ms latency in vendor material, ~150–200 ms in independent guides (conflict — see audit).
- Emotion / paralinguistic tags (`[laugh]`, `[sigh]`, etc.) and exaggeration control — useful for recruitment calls and videos.
- Every output carries Resemble's PerTh neural watermark — this is a feature for EU AI Act Art. 50 marking, not a bug.
- ~4–6 GB VRAM — fits the 6 GB GTX 1660 Super for development, and easily fits a 12–16 GB production card.

### 3.2 Alternatives considered

| Model | Licence | Why not primary in v1 |
|---|---|---|
| F5-TTS (official) | MIT code / CC-BY-NC-4.0 weights | Best English quality in independent tests, but non-commercial weights. Benchmark only. Using it in a product Mubashir sells or uses commercially would breach the licence. |
| OpenF5-TTS | Apache-2.0 | Community retrain on F5 architecture, commercial-safe on paper. Quality vs official F5-TTS UNVERIFIED. Evaluate in Phase 1 spike. |
| Qwen3-TTS 1.7B Base / 0.6B Base | Apache-2.0 | Excellent commercial-safe alternative: 3 s clone, 97 ms claimed first-packet, 10 languages. 1.7B is ~3.9 GB VRAM, 0.6B ~2.5 GB. Keep as English fallback if Chatterbox fails on US/GB accent separation. Does not solve Urdu. |
| Chatterbox Multilingual V3 500M | MIT | 23+ languages, but no Urdu. Use only if Turbo's English quality is worse than V3's on the same voice. |
| XTTS v2 | Coqui Public Model Licence (non-commercial) | Old reliable, 17 languages incl. Hindi, no Urdu officially. Non-commercial, no path to clearance (Coqui wound down 2024). Do not use. |
| CosyVoice 2 / Fun-CosyVoice 3.0 | Apache-2.0 (3.0) | Strong emotion control, 9 languages, no Urdu. Keep as Urdu fine-tune base candidate only. |
| Mistral Voxtral TTS | CC-BY-NC-4.0 (open release) | Claims to beat ElevenLabs, 90 ms, <5 s clone, 9 languages. Non-commercial open release. Benchmark only, same as F5-TTS. |
| Breeze TTS 2 | Research / non-commercial only | Highest Artificial Analysis Elo (1220) in Oct 2026, but non-commercial. Do not use. |

### 3.3 Accent strategy — the trap, and the fix

**Trap:** cloning copies the accent in the reference recording. One recording of Mubashir speaking in his natural accent will not magically produce a US voice and a British voice. ElevenLabs v4 has the same behaviour: accent is preserved when source and target match, and it aims for a natural accent in the target language otherwise — with no toggle announced.

**Fix in v1 — separate recordings, separate voice IDs:**
- Record `mubashir-en-us` with Mubashir deliberately speaking in a US accent.
- Record `mubashir-en-gb` with Mubashir deliberately speaking in a British accent.
- Do not attempt automatic accent conversion in v1. OpenVoice V2 has accent control (British / American / Indian / Australian) but is 1–12 s per sentence, not real-time, and is documented to flatten non-American accents to American. It is not a v1 dependency.
- Each accent gets its own reference clip set and its own benchmark. If the GB recording still sounds American to native GB listeners, the recording is re-done — the model is not blamed for the input.

---

## 4. Urdu engine choice

### 4.1 Decision (v1) — gated research spike, not a committed engine

**Urdu is the highest-risk part of v1. No Urdu engine is committed until the Phase 1 spike proves it can clone Mubashir's Urdu voice at acceptable quality.**

Primary candidates to test, in order:

1. **Kani-TTS-400M-UR / Kani-TTS 2 community Urdu** — Kani-TTS base is Apache-2.0, 400–450M parameters, LFM2-based, with a published LoRA fine-tune pipeline. The base model officially supports English, German, Korean, Arabic, Chinese, Spanish, Kyrgyz, Japanese (v1) / English, Spanish, Kyrgyz (v2). Urdu is a **community adaptation**, not an official language. Community reports claim production-level quality for Urdu, Vietnamese, Turkish, Creole adaptations. Licence and checkpoint for the specific Urdu variant are UNVERIFIED — must be confirmed from the exact Hugging Face repo before any use.
2. **DeepSpeak-v1** — Urdu TTS trained from scratch (rectified flow DiT, Qwen3.5-0.8B text backbone, reference-audio speaker conditioning, cloning from 3–15 s clips), described in the author's CV/portfolio. No public model card, licence, or Hugging Face link was verified in v1 research. Treat as a **lead to chase**, not a dependency. If no public checkpoint exists, it drops out.
3. **Matcha-TTS for Urdu** — cited in browser tools as the Urdu engine behind Kokoro-82M / Matcha-TTS Urdu voices. No verified cloning capability or licence for Mubashir's voice was established in v1. Test only as a fallback for intelligibility, not cloning.

### 4.2 Fallbacks (in order)

- **Fallback A — Piper `ur_PK`:** Piper engine is MIT, but each voice carries its own dataset licence and most are non-commercial. `ur_PK` Fasih (male) / Aegis (female) are fixed voices, not Mubashir. Use only to test Urdu text normalisation and pronunciation (numbers, loanwords, Roman Urdu). Never ship as `mubashir-ur`.
- **Fallback B — Fine-tune a permissive base on Urdu:** Take Fun-CosyVoice 3.0 (Apache-2.0, 0.5B) or Chatterbox Multilingual V3 (MIT) or Qwen3-TTS Base (Apache-2.0) and LoRA-fine-tune on Mubashir's 20 min Urdu + a public Urdu TTS corpus (if a commercially-clean one can be found). This is a Phase 2 research task, not a v1 promise. It may fail — Urdu grapheme-to-phoneme, Nastaliq script, and code-switching are all hard.
- **Fallback C — Ship English-only:** If no Urdu candidate passes the benchmark gate (see §9), v1 ships with `mubashir-en-us` and `mubashir-en-gb` only. Urdu is listed as "in research" in the README, not shipped.

### 4.3 Urdu text handling (v1 scope)

- Input must accept **both** Urdu script (اردو, RTL, Nastaliq) **and** Roman Urdu (Latin letters, e.g. "aap kaise hain").
- Roman Urdu is normalised to Urdu phonemes before synthesis — a deterministic transliteration table + exception dictionary for common words, built from the recording scripts. No claim that a general Roman-Urdu transliterator will be built in v1.
- Numbers: Western digits (0–9) and Urdu digits (۰–۹) both handled; phone numbers, prices in PKR, dates, and times read in Urdu.
- English loanwords inside Urdu sentences (e.g. "interview", "CV", "job") must be pronounced in English, not spelled out in Urdu phonemes. The normaliser tags loanwords and passes them through in English.
- Mixed-language sentences (code-switching) are supported as a stretch goal, not a v1 gate.

---

## 5. Recording plan — 60 minutes total

This is the owner's main dependency. No recording, no voice.

### 5.1 Format (non-negotiable)

- WAV, 48 kHz, 16-bit, mono. No MP3, no phone recordings, no compressed audio.
- Same microphone, same room, same distance, same gain for all three variants.
- Quiet room, no fan / AC / traffic in the background, no echo. Record in a small, soft-furnished room if possible.
- No clipping, no whispering, no shouting. Natural conversational volume, consistent across takes.
- Each sentence as a separate file, or one long file with a matching transcript and timestamps — decision at implementation. Separate files are preferred for dataset hygiene.
- File naming: `en-us_001.wav`, `en-gb_001.wav`, `ur_001.wav`, with a CSV/JSON manifest: `file, text, variant, duration_seconds`.

### 5.2 Amount

| Variant | Clean speech | Purpose |
|---|---|---|
| `mubashir-en-us` | 20 min | Zero-shot reference (5–10 s clips) + fine-tune pool |
| `mubashir-en-gb` | 20 min | Zero-shot reference + fine-tune pool |
| `mubashir-ur` | 20 min | Zero-shot reference + fine-tune pool |
| **Total** | **60 min** | |

Zero-shot cloning needs only 5–10 s, but 20 min per variant gives: (a) choice of the best reference clips, (b) coverage of phonemes, numbers, names, and (c) a fine-tune dataset if zero-shot is not close enough. Recording less than this and expecting a professional clone is a known failure mode.

### 5.3 Script content (to be written in implementation Phase 0)

Each variant's script must cover:
- Normal statements, questions (rising intonation), exclamations.
- Numbers: 1–100, years, phone numbers, salaries per hour (£12.50, $15), dates, postcodes (UK: "SW1A 1AA", "M1 1AE").
- Names: British names (e.g. "Kingsbury", "Sarah", "Mohammed"), Pakistani names, company names.
- Recruitment phrases for Xplogent: "Thank you for speaking with me today", "The role is in Manchester, about 12 miles from your postcode", "The pay is £13.50 per hour", "Would Tuesday at 10am work for an interview?"
- Product / video phrases for xplosole: tool names, "free, no signup", calls to action.
- Urdu script: everyday conversation, formal / polite forms, job-related phrases, numbers and prices in PKR.
- Roman Urdu: the same Urdu sentences written in Latin letters, so the normaliser can be tested on parallel text.

Scripts are **not** in this plan. They are a Phase 0 deliverable, to be written and reviewed by the owner before recording.

### 5.4 Consent and provenance

- Mubashir records a spoken consent statement on camera / audio at the start of each session: name, date, "I consent to my voice being cloned for use in my own products (Xplogent, xplosole, and future products I own)".
- A written consent file (`CONSENT.md` in the repo, private copy only — never commit the audio to a public repo) records the scope. The public repo must never contain his voice recordings.
- Recordings live in a private, encrypted store, not in `mubashiribstec/xploclone`. The repo holds code, config, and scripts only.

---

## 6. API design

### 6.1 REST — file generation

```
POST /v1/tts
  Authorization: Bearer <api-key>
  Content-Type: application/json
  {
    "voice_id": "mubashir-en-gb",
    "text": "Hello, this is a test of the British voice.",
    "format": "wav",            // wav | mp3 | pcm16
    "sample_rate": 24000,       // 24000 | 8000 (telephony)
    "speed": 1.0,               // 0.75 - 1.25, v1 only if engine supports it
    "emotion": "neutral"        // neutral | friendly | formal — mapped to engine tags, v1 best-effort
  }
  -> 200, audio/wav, streaming body
  -> 400 unknown voice_id / unsupported language / text too long (>5000 chars)
  -> 401 bad API key, 429 rate limited, 503 engine not loaded

GET /v1/voices
  -> [{ "voice_id": "mubashir-en-us", "language": "en-US", "accent": "US", "engine": "chatterbox-turbo" }, ...]
  // Only the 3 hardcoded voices. No create/delete endpoints in v1.

GET /health
  -> { "status": "ok", "engines": { "en": "loaded", "ur": "loaded|unavailable" }, "gpu": "..." }

GET /metrics
  -> Prometheus-style: requests, latency p50/p95, chars synthesised, errors by voice_id
```

### 6.2 WebSocket — live calls (Xplogent)

```
WS /v1/tts/stream
  Client -> Server (JSON):
    { "type": "start", "voice_id": "mubashir-en-gb", "sample_rate": 8000, "format": "mulaw" }
    { "type": "text", "text": "Hello, thank you for calling.", "utterance_id": "u-123" }
    { "type": "interrupt" }   // barge-in: stop current utterance immediately
    { "type": "end" }
  Server -> Client:
    { "type": "audio", "utterance_id": "u-123", "chunk": "<base64>", "format": "mulaw", "sample_rate": 8000 }
    { "type": "done", "utterance_id": "u-123", "duration_ms": 1840 }
    { "type": "error", "code": "...", "message": "..." }
```

- Audio is chunked by sentence / clause, not by whole paragraph. The first chunk must be sent as soon as it is ready — never wait for the full utterance.
- Telephony output: 8 kHz, G.711 μ-law, 20 ms frames, mono. The API does the resampling; Xplogent must not have to transcode.
- Interrupt must flush the TTS buffer and stop synthesis within <100 ms of receipt. This is a hard requirement for calls — a caller saying "Hello?" must not have to wait for a full sentence to finish.

### 6.3 Text normalisation (before the engine)

1. Detect script: Urdu script vs Roman Urdu vs English (by Unicode range + dictionary).
2. Expand numbers, dates, times, currency, abbreviations ("Dr." → "Doctor", "£13.50" → "thirteen pounds fifty").
3. Roman Urdu → Urdu phoneme mapping (dictionary + rules).
4. Tag English loanwords in Urdu text so they are spoken in English.
5. Split into sentences / clauses for streaming. Max sentence length enforced; long text is chunked, not rejected, up to the 5,000-char limit.

### 6.4 Limits (v1)

- Max text: 5,000 characters per REST request (same as ElevenLabs v3 limit — a useful parity point).
- Max concurrent syntheses: 1 on a single GPU in v1. Additional requests queue (FIFO, max queue 10, timeout 30 s) or return 503 with `Retry-After`. No silent degradation.
- Rate limit: 60 requests / minute per API key in v1 (tunable in config).
- No audio is stored by default. If `store_output=true` is passed (admin only), output is kept for 7 days for debugging, then deleted.

---

## 7. Web UI

Single-owner admin UI. Not a public product in v1.

Pages:
- **Generate:** pick voice (3 buttons, with flags / labels), type or paste text, pick format, Generate → audio player + Download WAV/MP3. Show latency, characters, engine used.
- **Voices:** the 3 voices, with a 10-second sample clip each, engine, and status (loaded / unavailable).
- **History:** last 50 generations (text snippet, voice, duration, latency, timestamp). No audio playback after 7 days unless stored.
- **API keys:** list, create, revoke. Show last-used time. Keys are shown once at creation.
- **Health:** GPU, VRAM used/free, engine status, queue depth, uptime.

Tech: Next.js 16.4.3 (App Router), Node.js 26.12.1, Tailwind CSS, no heavy component library in v1. The UI talks to the FastAPI backend via a thin BFF / proxy route — the browser never talks directly to the GPU server, and the API key never ships to the browser.

---

## 8. Infrastructure and deployment

### 8.1 Hosts

| Environment | Hardware | Purpose |
|---|---|---|
| Dev (owner's Z640) | HP Z640, GTX 1660 Super 6 GB VRAM, 16 GB+ RAM (32 GB recommended) | Local dev, zero-shot testing, recording QC. Can run Chatterbox Turbo (~4–6 GB) and Qwen3-TTS 0.6B (~3.9 GB) one at a time. Cannot run F5-TTS comfortably (needs ~12 GB), cannot run STT + LLM + TTS together on the same 6 GB card. |
| Prod v1 (single GPU) | Cloud GPU or a local server with ≥12 GB VRAM (RTX 4060 Ti 16 GB, RTX 5070, A10 / L4) | One concurrent call / generation. Decision on cloud vs local at implementation, based on cost for the owner's expected call volume. |
| CI | GitHub Actions, CPU only | Lint, type-check, unit tests, Docker build (no GPU tests in CI) |

### 8.2 Docker

- Base image: `nvidia/cuda:12.8.0-runtime-ubuntu24.04` (verify tag at build; 12.9 also exists — pin one, do not float).
- Python 3.14.10 in the image, `uv` for dependency management, lockfile committed.
- Two services in `docker-compose.yml`: `api` (FastAPI + engines) and `web` (Next.js). One `db` service only if PostgreSQL is added in Phase 2.
- GPU: `deploy.resources.reservations.devices: [{ driver: nvidia, count: 1, capabilities: [gpu] }]`.
- Healthcheck on `/health`, restart policy `unless-stopped`, logs to stdout (JSON).
- No secrets in the image or in git. API keys, model paths, and host config come from `.env` (gitignored) or the host's secret store.

### 8.3 Repo layout (planned, not yet created)

```
xploclone/
  PLAN-v1.md
  PLAN-v2.md
  AUDIT-v1.md (or audit section in PLAN-v1 — see §12)
  README.md
  .gitignore
  docker-compose.yml
  Dockerfile.api
  Dockerfile.web
  pyproject.toml
  apps/
    api/            # FastAPI app
    web/            # Next.js app
  packages/
    tts-core/       # engine abstraction, router, normaliser, audio utils
    tts-engines/
      chatterbox/   # Chatterbox Turbo adapter
      qwen3/        # Qwen3-TTS adapter (fallback)
      urdu/         # Urdu engine adapter (gated)
  scripts/
    record/         # recording scripts (text only, no audio)
    benchmark/      # blind-test harness vs ElevenLabs
  tests/
  docs/
    CONSENT-TEMPLATE.md
    BENCHMARK.md
```

---

## 9. Testing and benchmark plan vs ElevenLabs

### 9.1 What is measured

| Metric | How | Target (v1) |
|---|---|---|
| Naturalness (MOS) | Blind listening, 1–5 scale, owner + ≥2 native listeners per accent/language | EN ≥ ElevenLabs v4 Turbo; UR > ElevenLabs v3 |
| Speaker similarity (SIM) | Human rating + objective embedding cosine (e.g. speaker-verification embedding) | ≥0.80 cosine on held-out reference clips; human "sounds like Mubashir" |
| Intelligibility (WER) | Transcribe generated audio with Whisper, compare to input text | EN WER <5%, UR WER <10% (Urdu WER target is looser — verify at benchmark) |
| Latency — file | Time from request to first byte / to complete file | First byte <500 ms, complete <2 s for ≤500 chars on prod GPU |
| Latency — streaming | Time from WebSocket `text` to first audio chunk | <200 ms on prod GPU (TTS only, excluding LLM/STT) |
| Latency — end-to-end call | Caller finishes speaking → first word heard | <800 ms total (STT + LLM + TTS + network) — TTS is only one part |
| Cost per minute | GPU $/hour ÷ minutes generated per hour | Marginal cost ≈ $0 after GPU; compare to ElevenLabs $0.17–$0.20/min (Starter/Creator) and $0.034/min (v4 Turbo API) |
| Robustness | Long text, numbers, names, code-switching, noisy input text | No crashes, no infinite loops, no truncated sentences without an error |

### 9.2 Blind-test protocol

1. Write 10 test scripts per variant (30 total): 3 short (1 sentence), 4 medium (3–5 sentences), 3 long (paragraph), covering numbers, names, questions, recruitment phrases, and Urdu formal/informal.
2. Generate each script with (a) XploClone, (b) ElevenLabs v4 Turbo (EN) / v3 (UR, if v4 Urdu is not actually available — see audit), (c) ElevenLabs v4 (EN, quality mode).
3. Randomise order, strip metadata, present to listeners who do not know which is which.
4. Listeners score naturalness, accent correctness (US vs GB), and "sounds like the same person" for Urdu.
5. Record results in `docs/BENCHMARK.md` with audio file hashes, model versions, and dates. Do not cherry-pick the best take — report the first take, and separately note if a re-take was needed and why.

### 9.3 Gates

- **Gate 1 (Phase 1 end):** English zero-shot passes blind test vs ElevenLabs Flash on at least 7/10 scripts. If not, try Qwen3-TTS, then OpenF5-TTS, then fine-tune. If none passes, stop and re-plan — do not ship a worse English voice.
- **Gate 2 (Phase 2 end):** Urdu candidate passes blind test vs ElevenLabs v3 Urdu on at least 7/10 scripts, with WER <10%. If not, ship English-only and move Urdu to research.
- **Gate 3 (Phase 3 end):** Live-call streaming passes on a real phone line (not laptop speakers) with Xplogent, with barge-in working and no >800 ms turn gaps on a 5-minute test call.

---

## 10. Security, consent, watermarking, legal

- **Only Mubashir's voice.** The API has no voice-upload endpoint in v1. The only voices are the 3 hardcoded IDs, built from his own recordings with his written + spoken consent. This is the strongest safety control in the whole system — there is no way for a user to clone someone else through v1.
- **Watermarking:** Preserve Chatterbox's PerTh watermark on every English output. Do not strip watermarks. For the Urdu engine, if it has no watermark, add a metadata marker (e.g. ID3 / WAV LIST chunk: `XploClone-AI-Generated`) and log the generation. Watermark robustness (does it survive μ-law transcoding to 8 kHz?) is a test item — if it does not survive, note it as a limitation, do not claim compliance you do not have.
- **EU AI Act Art. 50:** In force 2 Aug 2026. XploClone is a new system (launched after 2 Aug 2026), so it has **no grace period** — it must mark synthetic audio in a machine-readable format from day one, and Xplogent calls using it must disclose to the caller that they are speaking to AI. The existing Xplogent greeting ("This call is recorded" + AI disclosure) must be kept. Fines up to €15M or 3% of worldwide turnover are cited for Art. 50 breaches — this is not legal advice, and the owner should confirm scope with qualified counsel before selling to EU/UK customers.
- **US / UK:** NO FAKES Act (US Senate) cleared committee in June 2026 but is not law as of Oct 2026. Tennessee ELVIS Act is in force. UK has no equivalent voice-clone statute in v1 scope, but fraud / impersonation laws still apply. The single-voice, own-voice design is the mitigation.
- **Data:** Recordings and embeddings are sensitive personal data. Store them encrypted at rest, access-logged, never in the public repo, never in a public bucket. Delete outputs after 7 days unless the owner explicitly keeps them. No audio in application logs.
- **Abuse:** API keys are per-client, rate-limited, and revocable. If a key is leaked, revoke it — do not try to "fix" it by adding a blocklist.
- **No secrets in chat or git.** API keys, GPU host credentials, and any ElevenLabs keys used for benchmarking live in `.env` / the host secret store, never in the repo and never pasted in chat.

---

## 11. Phased milestones

| Phase | Goal | Exit criteria |
|---|---|---|
| **Phase 0 — Spec & scripts (1 week)** | Write recording scripts (EN-US, EN-GB, UR + Roman UR), consent template, benchmark scripts, repo skeleton, CI | Scripts reviewed by owner; repo has README, .gitignore, CI passing on empty app |
| **Phase 1 — English MVP, file generation (2–3 weeks)** | Chatterbox Turbo running in Docker on dev GPU; REST `/v1/tts` returning WAV/MP3; web UI Generate page; blind test vs ElevenLabs | Gate 1 passed; first-byte <500 ms on dev GPU for ≤500 chars |
| **Phase 2 — Urdu spike + API (2–4 weeks)** | Test Kani-TTS Urdu and DeepSpeak-v1 (if available); test Piper baseline; build Roman Urdu normaliser; REST API for `mubashir-ur` | Gate 2 passed, or English-only ship decision recorded with reasons |
| **Phase 3 — Live-call streaming (2–3 weeks)** | WebSocket `/v1/tts/stream`, 8 kHz μ-law, sentence chunking, interrupt / barge-in; Xplogent integration on a test line | Gate 3 passed on a real phone line; end-to-end turn <800 ms |
| **Phase 4 — Fine-tune (if needed) (3–4 weeks)** | LoRA fine-tune per voice on the 20-min datasets, only if zero-shot is not close enough; re-benchmark | Fine-tuned model beats zero-shot on blind test by ≥0.5 MOS, or revert to zero-shot |
| **Phase 5 — Hardening & handover (1–2 weeks)** | Rate limits, metrics, backup/restore of voices, docs, audit of built project, fix issues | Audit of built project complete; all critical issues fixed or recorded as known limitations |

Total v1 estimate: **8–13 weeks** from Phase 0 start, assuming recordings are delivered on time and no Urdu engine has to be built from scratch. If Urdu needs a from-scratch fine-tune, add 4–8 weeks and re-estimate at Gate 2.

---

## 12. Risks (v1 list — to be expanded in audit)

1. Urdu engine may not exist as a usable, licensed checkpoint. (Highest risk.)
2. Accent separation may fail — GB recording may still sound American / Pakistani to native listeners.
3. Chatterbox Turbo latency claims conflict (75 ms vs 150 ms vs 470 ms in different sources) — real latency on the owner's GPU is unknown until measured.
4. 6 GB VRAM is marginal for live calls — STT + LLM + TTS cannot all run on the same card.
5. Python 3.15 is newest but PyTorch `torch.compile` does not work on it yet — version choice must be deliberate, not "latest".
6. FastAPI version conflict in sources (0.143.1 vs 0.162.0) — pin and verify at build.
7. F5-TTS / Voxtral / Breeze quality is tempting, but their weights are non-commercial — using them in a product is a licence breach, not a shortcut.
8. EU AI Act marking may not survive μ-law transcoding — watermark robustness is untested.
9. Single GPU = single point of failure. No HA in v1 by design, but the owner must know that a GPU failure = total outage.
10. Recording quality is the ceiling. A noisy, inconsistent, or rushed 60 minutes will produce a bad clone no model can fix.

---

## 13. Open questions for the owner (do not block Phase 0)

1. Where will the production GPU live — cloud (which provider?) or a local server the owner already has?
2. Is the web UI to be hosted on Vercel (like xplosole) or on the same host as the API?
3. For Xplogent calls, which voice is the default — GB for UK recruitment, US for US products, or configurable per campaign?
4. Should Urdu output be Urdu script by default, Roman Urdu by default, or chosen per request?

---

*End of PLAN-v1. Next step: audit this plan (§12 expanded), compare it to the real world, and produce PLAN-v2 with corrections and a decision log.*
