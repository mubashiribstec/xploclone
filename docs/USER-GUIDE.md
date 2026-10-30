# User Guide — XploClone web UI

The web UI is a **single-owner admin UI**, not a public service.
There is no signup. One owner password, set at install time.

## Log in

1. Install: `./install.sh` (prints the web password once — save it).
2. Open **http://localhost:3000/login**.
3. Enter the password. Correct → you land on Generate; wrong → 401.
   Unauthenticated visits to any page redirect to `/login`.

If you lost the password: generate a new hash
(`python3 -c "import hashlib; print(hashlib.sha256(b'NEW_PASSWORD').hexdigest())"`),
put it in `.env` as `XPLOCLONE_WEB_PASSWORD_HASH`, restart the web
service. There is no password reset by email.

## Generate (home page)

1. Pick a voice: `mubashir-en-us` or `mubashir-en-gb`.
   `mubashir-ur` is shown as "in research" and is not selectable —
   the Urdu engine is gated (see `docs/URDU-SPIKE.md`).
2. Type or paste text (max 5,000 characters — the counter shows it).
3. Generate. You get an audio player + download (WAV).
4. History (last 50, in your browser only) is listed under the form.

If a voice shows "unavailable", no reference clip is installed for
it yet — place the clip in `api/reference/` and restart the API
(see `docs/INSTALL.md`). Generation is rate-limited to 60 req/min
per web session.

## Voices page

Lists the 3 voices with language, accent, engine and status
(`loaded` / `unavailable`). There is no way to add a voice here —
XploClone serves Mubashir Ali's voice only, by design. Adding a
voice means recording it and wiring it in code, not clicking a
button.

## API keys page

Shows the API keys configured for the server-side proxy. Keys are
**env-managed**: values are never shown in the UI. To rotate a key,
generate a new key + hash, update `.env`
(`XPLOCLONE_API_KEY` / `XPLOCLONE_API_KEY_HASH`), restart the API
and web services. The key is for your own products (Xplogent,
xplosole) calling `POST /v1/tts` — see `docs/API.md` for the
curl examples. Never paste a key into a chat or a public repo.

## Health page

Shows API status (`ok` / readiness), device (`cuda` / `cpu`),
engine (`turbo` / `nano`), the pinned and resolved Chatterbox
revisions, and per-voice status. Use it to confirm which engine
is actually running — CPU mode must say `engine: nano`,
`device: cpu`. If it says Turbo on a CPU-only machine, your
`.env` still says `XPLOCLONE_DEVICE=cuda` — fix it and restart.

## What the UI cannot do (Phase 1)

- No Urdu generation, no dubbing, no voice changer, no MP3 output
  (WAV / PCM16 only via the API).
- No live-call streaming — that is Phase 3 (WebSocket, Xplogent).
- No user accounts, no billing, no public signup.
