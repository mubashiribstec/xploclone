# Third-party licences (NOTICE)

XploClone itself is MIT licensed — see `LICENSE` (Copyright (c) 2026
Mubashir Ali).

This project **uses** (at runtime, via `uv.lock` / `web/package-lock.json`)
the following third-party software, each under its own licence. The
software listed here is not redistributed as source by this repository;
consult each package's own licence file for its exact terms.

## Voice engine (the only model code this service loads)

- **Chatterbox Turbo** (`chatterbox-tts` git master 5de7a54, Hugging Face
  `ResembleAI/chatterbox-turbo`) — **MIT**, by Resemble AI. This is the
  English TTS engine for `mubashir-en-us` / `mubashir-en-gb`. Its PerTh
  watermark is preserved on every output; never strip it.
- **resemble-perth** 1.0.1 — the PerTh watermark library used by
  Chatterbox Turbo. Licence: see the `resemble-perth` package (MIT, as
  distributed on PyPI).

## Runtime libraries (selected — full pins in `uv.lock`)

- **PyTorch / torchaudio** — BSD-style licence (see the PyTorch project).
- **transformers** 5.2.0, **diffusers** 0.29.0 — Apache License 2.0.
- **huggingface-hub** 1.33.0 — Apache License 2.0.
- **FastAPI, Pydantic, Uvicorn, soundfile, NumPy, httpx** — MIT / BSD
  licences as distributed on PyPI.
- **Next.js, React, Tailwind CSS, sharp, TypeScript** (web UI) — MIT /
  Apache-2.0 licences as distributed on npm; see `web/package-lock.json`.

## Explicitly NOT in this repository

No F5-TTS, XTTS v2, Voxtral, or Breeze TTS 2 weights or code are shipped
in the production image — those models are non-commercial and are
benchmark-only (PLAN-v2 §3.2 / §12.5). No voice recordings, embeddings,
or API keys are committed anywhere in this repo.
