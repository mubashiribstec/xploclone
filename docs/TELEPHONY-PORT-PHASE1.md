# Telephony Port — Phase 1 (VoiceStudio → XploClone)

**Branch:** `muse/xploclone-telephony-port` (off `muse/xploclone-mvp`)
**Date:** 2026-11-05
**Source:** [debpalash/VoiceStudio](https://github.com/debpalash/VoiceStudio)
(`backend/services/telephony/audio.py`,
`backend/api/routers/tts_stream.py`,
`backend/services/telephony/session.py`), AGPL-3.0-only.
**Premise:** XploClone is a private, personal, non-commercial learning
project. Copying VoiceStudio *code* into this private repo for
learning is the permitted use the owner confirmed; no model weights
were copied (OmniVoice weights are CC-BY-NC and were never touched).
Every ported file carries a header stating its VoiceStudio origin and
licence. Obligations under AGPL-3.0 / CC-BY-NC would trigger only on
distribution, public network offering, or commercial use — none of
which this phase does.

## What was ported

| XploClone file | VoiceStudio source | What it is |
|---|---|---|
| `api/telephony_audio.py` (171 lines) | `backend/services/telephony/audio.py` (108 lines) | G.711 μ-law codec (`lin2ulaw`/`ulaw2lin`), 8 kHz resampling, `pcm16_to_ulaw`, frame splitting, μ-law→WAV preview |
| `api/telephony_stream.py` (393 lines) | `backend/api/routers/tts_stream.py` (533 lines) | Streaming TTS WebSocket `WS /v1/tts/stream`: start frame, 160-byte μ-law frames, done frame with measured TTFA + RTF |
| `api/telephony_session.py` (709 lines) | `backend/services/telephony/session.py` (649 lines) | Provider-agnostic call session: per-call tokens, sliding windows, call registry, greeting cache, `render_ulaw`, `run_call` media-stream driver |
| `api/rate_limit.py` (+15 lines) | — (XploClone's own) | Shared `RATE_LIMITER` / `SYNTHESIS_QUEUE` singletons so HTTP and WebSocket share one rate-limit bucket and one synthesis slot |
| `api/main.py` (+4/−4 lines) | — (XploClone's own) | Mounts the telephony router; HTTP endpoint now uses the shared singletons |
| `tests/test_telephony_audio.py` (161 lines) | — (new) | 16 tests |
| `tests/test_telephony_session.py` (463 lines) | — (new) | 23 tests |
| `tests/test_telephony_stream.py` (152 lines) | — (new) | 10 tests |

No existing XploClone code was deleted, renamed or truncated. The only
modified files are `api/main.py` and `api/rate_limit.py` (diffs below).

## Adaptations (not a blind copy)

**`telephony_audio.py`**
- `ulaw_to_wav` uses the stdlib `wave` module, not `soundfile`
  (XploClone's `api/audio.py` already does this).
- New helper `pcm16_to_ulaw` (PCM16 bytes in, μ-law bytes out) for the
  streaming path, so the WebSocket handler never handles torch tensors.
- `to_phone_ulaw` accepts torch tensors or numpy arrays.

**`telephony_stream.py`** — the endpoint speaks the phone line, not the browser:
- Output is 8 kHz μ-law in 20 ms (160-byte) frames, not 24 kHz PCM16
  in 200 ms chunks.
- Streams from XploClone's own Chatterbox Turbo engine, per sentence,
  through `render_ulaw` — no VoiceStudio module is imported anywhere.
- Auth is `?key=` on the WebSocket URL, constant-time compared like
  `POST /v1/tts`. VoiceStudio's route had no auth check of its own
  (local desktop app); an unauthenticated XploClone socket would have
  bypassed the Bearer auth of `/v1/tts`.
- Voice resolution is XploClone's 3 hardcoded voices; unknown voice
  and Urdu are errors, never a silent fallback (XploClone's standing
  rule — `mubashir-ur` returns 503 by design).
- The text pipeline is `POST /v1/tts`'s own
  (tag policy → normalise → humanise), normalised exactly once before
  chunking.
- The synthesis queue and rate limiter are the shared singletons
  (see `api/rate_limit.py`); the original used a GPU-pool guard
  XploClone does not have. The per-IP limiter stays HTTP-only.
- The done frame reports measured TTFA (request arrival → first audio
  frame on the socket) and a true RTF (per-sentence synthesis seconds
  per audio second — never wall clock, which would blame the engine
  for a slow client).

**`telephony_session.py`**
- No provider adapter yet (Twilio is Phase 2): `MediaStreamProvider`
  is the contract a Phase 2 adapter must satisfy. `run_call` is
  ported and tested with a fake provider; no route wires it to a real
  provider in this phase.
- `_speech_key` resolves voices through XploClone's own registry
  (reference-clip stat) — no voice-profile DB.
- `render_ulaw` takes an injectable synthesizer (default: XploClone's
  Chatterbox Turbo stream) so tests run without a model/GPU. The text
  passed in must already be normalised; `render_ulaw` chunks it, it
  does not normalise. Concurrent renders of the same greeting share
  one synthesis (single flight); completed renders are cached.
- The end-of-playback mark is renamed `xploclone-end` (the original
  used `voicestudio-end`); both ends of the protocol live in this
  module, so the rename is safe.
- Call identifiers are kept only as a masked suffix in the status list;
  nothing here stores phone numbers or caller audio.

**`api/rate_limit.py` / `api/main.py`**
- `RATE_LIMITER` and `SYNTHESIS_QUEUE` are module-level singletons.
  `main.py` uses them instead of constructing its own instances.
  Two queues would let an HTTP request and a WebSocket stream
  synthesise at the same time and break the 1-at-a-time invariant;
  two rate limiters would give one key 60 req/min on each surface.
  The per-IP limiter (`ip_limiter`, pre-auth flood guard) is
  intentionally still constructed in `main.py` — it is HTTP-only.

## Audit fixes (found while porting / verifying)

1. **`lin2ulaw` validates its input** (audio). The original cast
   blindly to int16, silently wrapping out-of-range integers and
   truncating floats into wrong μ-law bytes. The port rejects float
   input with `TypeError` and clips integers to the int16 range.
2. **`resample_to_phone` sanitises non-finite samples** (audio). The
   original let NaN/inf through into phone audio.
3. **`resample_to_phone` imports torch only when resampling is
   actually needed** (audio). The port's first draft imported torch
   before the 8 kHz passthrough, so even a no-op call needed torch
   installed. Now the passthrough and the bad-rate check run without
   torch. Found by the test run: the 8 kHz tests failed with
   `ModuleNotFoundError: torch` until this was fixed.
4. **Malformed JSON keeps the socket open** (stream). The original
   dropped the connection on any receive error; the port answers an
   error frame and waits for the next request.
5. **Text is capped at `SETTINGS.max_chars` (5,000) and must be a
   string** (stream). The original accepted any length and any JSON
   type.
6. **Voice is checked before length** (stream). Unlike `POST /v1/tts`
   (length first), so the `text_too_long` metric always has a known
   voice id. Documented in the code.
7. **`gen_time_s` is reported at microsecond precision, not 1 ms**
   (stream). With 3 decimals a fast render rounded `gen_time_s`
   below `ttfa_ms`, which is impossible (TTFA is measured inside the
   same interval) and looked like a bug. Found by the test run:
   `ttfa_ms 4.2 > gen_time_s 0.004 * 1000`.
8. **The 0x7F/0xFF dual-zero is pinned, not papered over** (audio
   tests). μ-law has two codes for PCM 0; the encoder canonically
   picks 0xFF. `audioop` behaves identically — the test asserts the
   quirk explicitly instead of weakening the round-trip test.
9. **No silent voice fallback anywhere** (stream + session). The
   original resolved any voice string through a profile DB; the port
   errors on unknown voices and on Urdu (engine gated by design).

## Verification (measured, CPU-only, 2026-11-05)

Environment: this VM, Python 3.12.3, 4 CPU cores, no GPU, no torch
installed. Venv with pinned `fastapi 0.162.0`, `pydantic 2.14.2`,
`pytest 8.3.4`, `httpx 0.28.1`, `numpy 2.5.4`. No model weights were
downloaded; the engine is faked with a sine tone (see "Not verified").

- `python -m py_compile` on all 5 ported/modified files and all 3
  test files: **pass**.
- New tests: **49 passed** (`tests/test_telephony_audio.py` 16,
  `tests/test_telephony_session.py` 23,
  `tests/test_telephony_stream.py` 10).
  - Codec bit-identity vs `audioop` (available on Python 3.12):
    random PCM16 (sizes 0/1/2/100/4096, seeded), edge values, and all
    256 μ-law codes — **byte-identical in every case**. CPython
    golden vectors (VoiceStudio's own) pass and are the permanent pin
    for Python 3.13+, where `audioop` no longer exists.
  - WebSocket: happy path (start → 5× 160-byte frames → done with
    measured `ttfa_ms`/`rtf`), missing/wrong key → `unauthorized` +
    close 1008, empty text, over-long text, unknown voice, Urdu →
    `engine_unavailable` (no fallback), malformed JSON and non-object
    JSON → error frame with the socket staying open, two turns on one
    socket.
  - Session: `render_ulaw` output bytes, greeting-cache repeat (1
    synthesis for 2 renders), single-flight concurrency (1 synthesis
    for 2 concurrent renders), engine-error propagation, token
    single-use/binding/expiry/epoch/max-pending, sliding window,
    registry capacity, LRU cache eviction, `run_call` with a fake
    provider — rejected token, wrong account, refused factory, busy
    registry, completed call (160-byte frames + `xploclone-end`),
    caller hang-up, Clear/Mark barge-in flow, time limit.
- Full existing suite with the port applied: **173 passed, 1 skipped**
  — the standing baseline was 124 passed / 1 skipped, so the 49 new
  tests add exactly, and nothing regressed. (`test_acoustic_profile`
  and `test_similarity` need the repo's `scripts/` tree on the path;
  that is a test-tree requirement, not a failure — both pass here.)

## Not verified (honest gaps — needs a GPU / real provider)

- Real Chatterbox Turbo synthesis through the WebSocket: the engine
  is faked (sine tone) in every test. TTFA/RTF numbers in tests are
  fake-engine numbers (single-digit ms), not production numbers.
- Real torchaudio resampling at 24 kHz: torch is not installed here,
  so the 24 kHz resample path is stubbed in tests (decimation +
  real `lin2ulaw`); only the 8 kHz passthrough runs for real. The
  resample quality (anti-aliasing above 4 kHz) is torchaudio's, not
  re-proven here.
- No live phone call: `run_call` is exercised only against a fake
  provider. Twilio audio, barge-in on a real line, and the 200 ms
  endpointer are Phase 2 work.
- The blind-test protocol (SIM ≥ 0.80) does not apply to this phase:
  no voice is cloned here; the codec and the plumbing are
  voice-independent.

## Deliberately left for Phase 2

`agent.py`, `twilio.py`, `calls.py`, `gateway.py` (Twilio call agent,
provider adapter, outbound calls, SSE gateway) — **not ported**.
Also left out: the barge-in endpointer (needs live audio), the
greeting/announcement HTTP routes, outbound-call scheduling, and any
production deployment. Phase 2 should: write the Twilio adapter
against `MediaStreamProvider`, wire `run_call` to a route, test
against a real Twilio number on a dev account, and measure TTFA/RTF
with the real Chatterbox Turbo engine on a GPU.
