# User Guide — XploClone web UI

The web UI is a **single-owner admin UI**, not a public service.
There is no signup. One owner password, set at install time.

## Log in

1. Install: `./install.sh` (prints the web password once — save it).
2. Open **http://localhost:3000/login**.
3. Enter the password. Show / Hide toggles the password visibility.
   Correct → you land on Generate; wrong → 401 with an error message.
   Unauthenticated visits to any page redirect to `/login`.
4. Sign out from the top nav (Sign out button, top right). Signing out
   clears the session cookie and returns you to `/login`.

If you lost the password: generate a new hash
(`python3 -c "import hashlib; print(hashlib.sha256(b'NEW_PASSWORD').hexdigest())"`),
put it in `.env` as `XPLOCLONE_WEB_PASSWORD_HASH`, restart the web
service. There is no password reset by email.

## Generate (home page)

1. Pick a voice: `mubashir-en-us` or `mubashir-en-gb`.
   `mubashir-ur` is shown as "in research" and is not selectable —
   the Urdu engine is gated (see `docs/URDU-SPIKE.md`).
2. Pick a style preset: Natural (recommended), Warm, Firm, or Default.
   Advanced prosody (exaggeration, CFG, temperature, top-p, repetition
   penalty) opens in a collapsible panel; a "Custom" badge appears if
   you move a slider away from the preset, and "Reset to preset"
   restores it.
3. Type or paste text (max 5,000 characters — the counter shows it),
   or load a sample (Greeting, Recruitment call, Long-form test).
   Copy text and Clear text both work.
4. Generate. You get an audio player, file size, latency, preset and
   watermark status, plus Download WAV and Re-generate buttons.
5. History (last 50, in your browser only) is listed under the form.
   Each entry has Load (puts its full text, voice and preset back into
   the form) and Delete. Clear history asks you to click again to
   confirm. History is empty until your first generation.

If a voice shows "unavailable", no reference clip is installed for
it yet — place the clip in `api/reference/` and restart the API
(see `docs/INSTALL.md`). Generation is rate-limited to 60 req/min
per web session. If the API is down, Generate shows the error with a
Retry button instead of failing silently.

## How to get a human voice (not AI-sounding)

Robotic/flat delivery is a prosody failure, not a volume or
clarity problem. Three things decide whether the output sounds
human — in this order:

1. **The reference recording.** A monotone clean read produces a
   monotone clone. Record with natural range: neutral, warm, firm,
   questioning — conversational, not acted drama. Vary pace and
   emphasis; do not over-enunciate. See `docs/recording-scripts/`
   section H. A 60-second proxy clip unblocks testing; the full
   20-minute set is needed for Gate 1.
2. **The preset.** Start with **Natural** (the recommended default).
   Warm is softer/friendlier, Firm is steadier/more formal. Higher
   exaggeration = more human variation, lower CFG = less anchored to
   the reference. Change ONE knob at a time (advanced sliders) and
   re-listen to the SAME script — never change two knobs at once.
   Honest note: Chatterbox Turbo 0.1.7 ignores exaggeration/CFG, so
   presets work through sampling variation (temperature/top-p) on
   this engine. The UI says so next to the sliders.
3. **The script.** Write short sentences, one idea per sentence.
   Use commas for short pauses, full stops for longer ones, line
   breaks for the longest. The API preserves those as different
   pauses and splits over-long sentences automatically. `[laugh]`,
   `[sigh]`, `[chuckle]`, `[gasp]`, `[cough]` are the only tags that
   pass through — anything else is stripped.

Then prove it with ears, not numbers: a blind listen (owner + ≥ 2
native listeners, randomised order, same script across presets) and
the long-form test (2+ minutes continuous, SIM at start vs end —
see `docs/BENCHMARK.md` and `scripts/benchmark/similarity.py`).
SIM ≥ 0.80 is a speaker check, not a quality check — a flat clone
can score high SIM and still sound wrong.

## Voices page

Lists the 3 voices as cards with language, accent, engine and status
(`Ready` / `Unavailable` / `In research`), plus a last-checked time
and a working Refresh button. Each ready voice has a "Use this voice →"
button that opens Generate with that voice pre-selected. Urdu's card
explains it is disabled until the spike passes — there is no dead
button. There is no way to add a voice here —
XploClone serves Mubashir Ali's voice only, by design. Adding a
voice means recording it and wiring it in code, not clicking a
button.

## API keys page

Shows the API keys configured for the server-side proxy. Keys are
**env-managed**: values are never shown in the UI. Copy buttons copy
the API endpoint URL and a curl example (neither contains a secret).
To rotate a key, follow the numbered rotate instructions on the page
(generate a new key + hash, update `.env`
(`XPLOCLONE_API_KEY` / `XPLOCLONE_API_KEY_HASH`), restart the API
and web services). The key is for your own products (Xplogent,
xplosole) calling `POST /v1/tts` — see `docs/API.md` for the
curl examples. Never paste a key into a chat or a public repo.

## Health page

Shows API status (`ok` / readiness), device (`cuda` / `cpu`),
engine (`turbo` / `nano`), the pinned and resolved Chatterbox
revisions, and per-voice status, as status cards with a last-checked
time. Refresh re-fetches live from `GET /health` (via the web
`/api/health` proxy). Use it to confirm which engine
is actually running — CPU mode must say `engine: nano`,
`device: cpu`. If it says Turbo on a CPU-only machine, your
`.env` still says `XPLOCLONE_DEVICE=cuda` — fix it and restart.

## What the UI cannot do (Phase 1)

- No Urdu generation, no dubbing, no voice changer, no MP3 output
  (WAV / PCM16 only via the API).
- No live-call streaming — that is Phase 3 (WebSocket, Xplogent).
- No user accounts, no billing, no public signup.
