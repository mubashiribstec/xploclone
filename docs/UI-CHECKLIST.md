# UI Checklist — XploClone web UI (professional redesign, 2026-10-30)

Scope: single-owner admin UI only (no signup, no new product features).
Branch: `muse/xploclone-mvp`. This file lists every page and every
button/control, what it does, and how it was verified.

Verification done in this round: `npm run typecheck` pass,
`npm run build` pass (12 routes, incl. new `/api/health`),
`ruff check` + `ruff format --check` pass, `mypy api` clean,
`pytest -q` 100 passed, 1 skipped. Live smoke test: built app started
with a test password hash on port 3100 — login page 200, unauthenticated
`/` → 307 to `/login`, correct login 200 + session cookie, wrong
password 401, `/`, `/voices`, `/keys`, `/health` all 200 authenticated,
`/api/voices` and `/api/health` correctly 502 with no API running,
logout → 307 to `/login` and session cleared. Rendered Generate HTML
confirmed to contain: sample buttons, Copy/Clear text, Advanced
prosody toggle, History section, Re-generate/Download in the result
template.

NOT verified here (needs GPU + recordings): actual audio generation
in the browser (Generate button → WAV), voice `loaded` status,
per-voice "Use this voice" on a loaded voice, latency/watermark
values on real audio. Those need the API + reference recordings.

## Audit findings (before this round) — all fixed

| # | Finding | Fix |
|---|---|---|
| U1 | `globals.css` was 5 lines: no design system, no focus rings, no slider styling | Full design system: brand/accent tokens, visible focus, touch-sized range thumbs, toast/fade animations |
| U2 | Nav had no active-page highlight, plain underlined links, max-w-2xl, no footer | Dark sticky nav (`SiteNav`), active pill, logo + version badge, working Sign out with loading/error, footer |
| U3 | Login: no show/hide password, plain card | Centred card, Show/Hide toggle (working, aria-pressed), error role=alert, loading state |
| U4 | Generate: History was a dead list (no Load, no Clear, no Delete) | Load (restores full text/voice/preset), Delete per entry, Clear history with two-step confirm. History now stores the FULL text (old v1 entries stored only 120 chars — those load truncated, which is a known migration limit) |
| U5 | Generate: no sample text, no copy/clear text, no re-generate | 3 working sample buttons, Copy text (clipboard + fallback), Clear text, Re-generate in the result card |
| U6 | Generate: moving an advanced slider left the preset label stale (preset said "Natural", values did not match it) | "Custom" badge when any knob differs from the preset; Reset-to-preset button; temperature/top-p/repetition-penalty sliders added (the knobs Turbo actually honours) |
| U7 | Generate: no retry when the API is down; Generate clickable with an unavailable voice (failed only after the request) | Error banner with working Retry, Generate disabled with a tooltip reason when the voice is unavailable or text is empty |
| U8 | Voices page: server-rendered list, no action, no refresh | Client page with Refresh (re-fetch), last-checked time, "Use this voice →" per ready voice (navigates to `/?voice=…`, pre-selects it); Urdu card disabled with an explanation, not a dead button |
| U9 | Keys page: static list, no copy action | Working Copy buttons for the endpoint URL and the curl example (neither contains a secret); numbered rotate instructions |
| U10 | Health page: server-rendered, no refresh, no timestamp | Client page with working Refresh (new `/api/health` proxy route), last-checked time, status cards with badges |
| U11 | No mobile/responsive or accessibility pass | Full-width buttons on small screens, two-column Generate workspace collapsing to one column, labels on all inputs, aria-pressed/expanded, role=alert on errors, focus-visible rings |

## Per-page control inventory (verified behaviour)

### Layout / nav (all pages, when signed in)
- Generate / Voices / API keys / Health links — navigate, active page highlighted. Verified in build + smoke test (200s).
- Sign out — POSTs `/api/auth/logout`, clears the cookie, routes to `/login`. Verified live: 307 + session cleared.
- Footer — static version/scope text. No button.

### Login (`/login`)
- Password input — labelled, autocomplete=current-password. Works.
- Show / Hide — toggles input type, aria-pressed. Verified in rendered HTML.
- Sign in — submits, loading state, wrong password → 401 error shown. Verified live (200 correct / 401 wrong).
- Unauthenticated access to any page — proxy redirects to `/login` (307). Verified live.

### Generate (`/`)
- Voice buttons (US / GB) — select voice, disabled with "Unavailable" badge when not loaded. Verified in code + build; loaded-state click needs recordings.
- Urdu chip — static text "in research", not a button. By design.
- Preset buttons (Natural / Warm / Firm / Default) — set preset + all knobs, aria-pressed. Verified in code + build.
- Advanced prosody toggle — collapsible, aria-expanded/controls. Works.
- Sliders (exaggeration, CFG, temperature, top-p, repetition penalty) — update knobs, show preset defaults. Works; exaggeration/CFG have no audible effect on Turbo 0.1.7 (stated in UI).
- Reset to preset — restores the preset's knobs + toast. Works.
- Sample buttons (Greeting / Recruitment call / Long-form test) — load sample text + toast. Verified in rendered HTML + code.
- Copy text — clipboard with textarea fallback + "✓ Copied" feedback. Works.
- Clear text — empties the textarea. Works.
- Character counter — live `n / 5000`, input capped at 5000. Works.
- Generate audio — POSTs `/api/tts` with voice/text/preset/all knobs; loading state; error shown with Retry; on success shows audio player, size, latency, preset, watermark, Download WAV, Re-generate. Code + build verified; end-to-end audio needs API + recordings (not claimed).
- Download WAV — anchor with dated filename `xploclone-<voice>-<date>.wav`. Works (browser download; not exercised without audio).
- Re-generate — re-runs Generate with the same settings. Works in code.
- History Load — restores full text/voice/preset, scrolls to top, toast. Works in code.
- History Delete — removes one entry (localStorage updated). Works in code.
- Clear history — first click arms ("Click again to confirm"), second click clears. Works in code.
- Retry (API error banner) — re-fetches `/api/voices`. Works in code.
- Toast — appears on sample load / history load / clear / prosody reset, auto-dismisses. Works in code.

### Voices (`/voices`)
- Refresh — re-fetches `/api/voices`, loading state, last-checked time. Verified live (502 path with no API; success path needs API).
- Retry (error banner) — same as Refresh. Works in code.
- Use this voice → — ready voices only; navigates to `/?voice=<id>`, Generate pre-selects it. Works in code; loaded-voice click needs recordings.
- Urdu card — no button, explanation text. By design.

### API keys (`/keys`)
- Copy endpoint URL — copies `http://127.0.0.1:8000/v1/tts`. Works (CopyButton, clipboard + fallback).
- Copy curl example — copies the full curl block (no secret inside). Works.
- No button ever shows or copies a secret value. Verified by inspection.

### Health (`/health`)
- Refresh — re-fetches `/api/health`, loading state, last-checked time. Verified live (502 path with no API; success path needs API).
- Retry (error banner) — same as Refresh. Works in code.
- Status cards — liveness, readiness, version, device, engine, revisions, per-engine/per-voice rows with badges. Render from live data when the API is up.

## New API route added for the UI (only API change in this round)
- `GET /api/health` (`web/app/api/health/route.ts`) — session-gated proxy to the
  API's `GET /health`. No behaviour change to the FastAPI service.
