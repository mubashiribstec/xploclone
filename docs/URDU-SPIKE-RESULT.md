# Urdu Spike — Result

Date: 2026-10-31. Spike owner: Muse (subagent). Status: **COMPLETE — verdict FAIL**
(see §5). Dia-1.6B-Urdu could not be tested for cloning on this VM (§6).

Spike rule (PLAN-v2 §4.1, `docs/URDU-SPIKE.md`): a candidate passes only with
exact repo URL, licence file, checkpoint hash, **and a 30-second Urdu sample
in the owner's voice**. A lead without a download is a FAIL. Shipping a Hindi
voice as `mubashir-ur` is forbidden. Shipping a generic Urdu voice as
`mubashir-ur` is equally not a pass.

Test environment: this VM — no GPU, 2 CPU cores, 7.7 GB RAM.
Reference voice throughout: the owner's own Urdu WhatsApp note,
`workspace/user/files/PTT-20261030-WA0006_2_1yfz.opus` (14.73 s, Opus 48 kHz
mono), converted to `xploclone-sample-test/his-voice/ref-14s.wav` (48 kHz
16-bit mono WAV). Never copied into the repo.
Intelligibility judge: Whisper-base transcription (openai/whisper-base, CPU).
Speaker judge: ECAPA-TDNN cosine similarity (`scripts/benchmark/similarity.py`,
`speechbrain/spkrec-ecapa-voxceleb`), Gate 1 target SIM ≥ 0.80. SIM is a
speaker check, not a quality check.

## 1. DeepSpeak-v1 — FAILS the voice test (Urdu works, his voice does not)

- Repo: https://huggingface.co/mahwizzzz/deepspeak-v1 (author Muhammad Mahwiz
  Khalil, Proxima AI). Licence: **Apache-2.0**. Repo commit:
  `df4e2b1e82f46a97f373920fc83ce29dc23ec795`.
- Checkpoint: `model.pt`, 7,532,929,617 bytes, LFS SHA-256
  `e7386a3f2ec1e816c5b1f2132e588ff550c9ecc20388190a536fa228bcf505af`
  (downloaded + verified 2026-10-31). Mostly optimizer state (Muon): the
  model itself is 814,446,624 params, fp32, 613 tensors. Checkpoint step is
  **36,000**, not the 18,000 the model card claims — the card is stale.
- Runtime: Aratako Irodori-TTS (MIT, https://github.com/Aratako/Irodori-TTS),
  `irodori_tts.inference_runtime` (ref-audio zero-shot cloning interface).
  Codec: Aratako/Semantic-DACVAE-Japanese-32dim (MIT), `weights.pth`
  429,620,065 bytes, SHA-256
  `db120339c5ee7eca1912cdf29bc612b947a0808e69c3cebfb4936b45a762c1d5`
  (verified). Text backbone Qwen/Qwen3.5-0.8B (Apache-2.0).
- Test notes (CPU-only): full 7.5 GB `.pt` cannot be `torch.load`ed on a
  7.7 GB VM; slimmed to weights-only (3.26 GB fp32), then to bf16 (1.63 GB)
  because fp32 peaks ~7 GB (checkpoint + model copy) and gets OOM-killed.
  Runtime refuses bf16 on CPU — patched in the test script only (AVX512_BF16
  present on this AMD EPYC). torchaudio 2.11 `load` hard-requires torchcodec,
  which cannot load its native libs here — patched `torchaudio.load/save`
  to soundfile-backed versions in the test script only. These are test-harness
  workarounds, not product code. Runtime loaded in ~39–72 s.
- Samples (all 48 kHz, `xploclone-urdu-test/deepspeak/`):
  - `short-ur-script.wav` — 5.84 s, gen 203.7 s. Text: "السلام علیکم، میرا نام
    مبشر ہے۔ میں آپ کی مدد کے لیے یہاں ہوں۔" Whisper: "آل آلیکم میرام مباشر
    ہے، میں آپ کی مدد کے مدد کے مدد کے لئے یہاں ہوں۔" — intelligible, with a
    repetition stutter ("مدد کے مدد کے مدد کے").
  - `long-ur-script.wav` — 16.24 s, gen 472.0 s. Four-sentence passage.
    Whisper recovers the same content throughout (greeting, Lahore/Pakistan,
    free online tools, "آج میں اردو میں بات کر رہا ہوں… مصنوعی نہیں") with
    garbled edge words. Intelligible with effort.
  - `short-roman-urdu.wav` — 3.68 s, gen 167.5 s. Text: "Assalam o alaikum,
    mera naam Mubashir hai…" Whisper: "لطول ایک ما استارل کنت انا فلان سمکا
    پوسطایمی دنچا" — unintelligible babble. **Roman Urdu fails**, as the model
    cards warn.
- **Speaker similarity (ECAPA-TDNN) vs the owner's reference:**
  short 0.0624, long 0.1627, Roman 0.1114. Gate 1 target 0.80.
  Controls (same pipeline): ref-vs-ref 1.0; ref vs the earlier Chatterbox
  Nano clone of the same reference 0.661; DeepSpeak short-vs-long 0.8098
  (the two DeepSpeak samples are the same voice as each other); ref vs
  Piper (unrelated voice) 0.0831. DeepSpeak's scores sit at the
  unrelated-voice floor. **The output is a consistent Urdu voice, but it is
  not his voice** — speaker conditioning from the 14.7 s reference is not
  taking effect at this training stage (36k/100k steps, experimental).
- Verdict on DeepSpeak-v1: **FAIL as a cloning candidate.** Urdu synthesis
  works and is licensed and downloadable, but it does not clone the owner.
  Re-test after further training (author-side), not now.

## 2. Kani-TTS Urdu (kani-tts-400m-ur) — FAILS as a cloner (fixed voice)

- Repo: https://huggingface.co/mahwizzzz/kani-tts-400m-ur, Apache-2.0, commit
  `6f758dcedff6f33d74dacebab2876b3e536b8c89`, base
  `nineninesix/kani-tts-450m-0.2-pt`, trained on dataset `mahwizzzz/UAT`
  (20,444 clips, `file_name` + `text` only — no speaker column).
- The `kani-tts` 1.0.1 package exposes no reference-audio / zero-shot cloning
  parameter — only `speaker_id` selection for multi-speaker models, and the
  base card states "This model NOT support multiple speakers". The Urdu
  fine-tune is a single fixed voice. **Cannot clone the owner — fails the
  spike's cloning requirement.** Not downloaded (no test would change this).
  Same category as Piper: a generic Urdu voice, not his.

## 3. Piper ur_PK (fasih-medium) — baseline PASS (intelligibility only)

- Voice: `rhasspy/piper-voices` `ur/ur_PK/fasih/medium/ur_PK-fasih-medium.onnx`
  (64.8 MB, 22,050 Hz, single speaker, espeak phonemes). Piper engine MIT;
  voice licence per rhasspy/piper-voices.
- Sample: `xploclone-urdu-test/piper/baseline-ur-script.wav`, 3.36 s.
  Same sentence as the DeepSpeak short test. Whisper: "سلام علیکم میرا نام
  مبشر ہے میں آپ کی مدد کے لئے یہاں" — near-perfect transcription.
  **Urdu text → intelligible speech is proven.** Fixed voice, NOT the
  owner's clone — labelled as such, never to be shipped as `mubashir-ur`.

## 4. Other candidates noted (not tested — no cloning path found)

- `mahwizzzz/F5-TTS-UR` (MIT, `model_7378.pt`, 0 downloads) and
  `mahwizzzz/orpheus-urdu-tts` (MIT, 3B, 169 downloads): Urdu fine-tunes of
  F5-TTS / Orpheus, no evidence of a zero-shot reference-audio cloning
  path in their cards; not tested in this spike. F5-TTS does support
  reference-audio cloning in general — if DeepSpeak and Dia both fail,
  F5-TTS-UR is the next thing to check, but it is a separate spike.
- `mahwizzzz/vits-ur`, `mahwizzzz/stable-tts-urdu`: single-voice models,
  no cloning path.

## 5. Verdict: FAIL

No licensed model tested here clones the owner's Urdu voice. DeepSpeak-v1
generates intelligible Urdu script speech but not his voice (SIM 0.06–0.16,
at the unrelated-voice floor); Kani-UR and Piper are fixed voices; Dia-1.6B-Urdu
loads correctly but its cloning could not be tested on this CPU-only VM (§6).
**Urdu (`mubashir-ur`) does not ship.** Fallback order (PLAN-v2 §4.2):

- (B) **Fine-tune a permissive base** — the next step. Candidates: LoRA
  fine-tune of a multilingual base (Chatterbox Multilingual V3, Qwen3-TTS,
  or F5-TTS) on his Urdu recordings; or check `mahwizzzz/F5-TTS-UR` (MIT),
  an Urdu F5-TTS fine-tune — F5-TTS natively supports reference-audio
  cloning, so if that checkpoint preserves the cloning path it may work
  where DeepSpeak did not. Needs his Urdu recordings (20 min set per plan)
  and a GPU.
- (C) **Ship English-only** — acceptable v1 outcome. Urdu stays a Phase 2
  item.
- **Not an option:** a Hindi voice or a generic Urdu voice (Piper/Kani)
  labelled as `mubashir-ur`.

What would change the verdict: a GPU run of Dia-1.6B-Urdu with his voice as
audio prompt (the one untested cloning path), or a DeepSpeak re-test after
the author trains further (checkpoint is at 36k/100k steps; the card's
18k figure is stale), or a working F5-TTS-UR cloning test.

## 6. Dia-1.6B-Urdu — loads, but cloning UNTESTED (CPU impractical)

- Repo: https://huggingface.co/mahwizzzz/Dia-1.6B-Urdu, Apache-2.0, commit
  `9576ef5c4fac0d307b42ffe47586bcc6cb52ef55`. Checkpoint `model.pth`
  3,222,473,535 bytes, LFS SHA-256
  `5c4593333f35f44c455db2117e6022bc0fcd77ba6b903c801f4b93a832883387`
  (downloaded + verified 2026-10-31). Base `nari-labs/Dia-1.6B` (Apache-2.0).
  Dia supports voice cloning via audio prompt + prompt transcript (`[S1]` tags).
- Prompt transcript (Whisper-base, uncertain words) saved to
  `xploclone-urdu-test/dia-urdu-transcript.txt`. Test script:
  `xploclone-urdu-test/run_dia.py` (diagnostic: `run_dia_diag.py`).
- Loading works: the Urdu repo's `config.json` is only a metadata stub, and
  the base repo's config is a training config — the working combination is
  the `nari-labs/Dia-1.6B-0626` DiaConfig + the Urdu `model.pth`, loaded via
  a manual mmap load (plain `torch.load` OOM-kills this VM: 3.22 GB
  checkpoint + 3.22 GB model copy). `load_state_dict: missing=0
  unexpected=0` — the Urdu weights match the Dia 1.6B architecture exactly.
  Model loads in ~17–32 s on CPU (fp16).
- **Generation could not complete on this VM.** Dia's `_pad_text_input`
  pads every text to `max_position_embeddings` = 3072 tokens, so the encoder
  forward runs over a 3072-token sequence (mostly padding) with a
  3072×3072 attention mask — on 2 CPU cores in fp16 (with RMSNorm
  dtype-mismatch fallbacks) the encoder forward alone ran >12 min with no
  output, and a no-prompt diagnostic (172 tokens, ~2 s audio) also produced
  nothing after 4+ min. The full clone test (1264-token audio-prompt prefill
  + ~500 autoregressive decode steps) would take 30–60+ min per sample here.
  Killed after ~20 min with no generation output. This is a CPU-vs-design
  limitation, not a model failure: Dia is built for GPU inference.
- Also fixed along the way: `torchaudio.load` needs torchcodec (unloadable
  here) — patched to soundfile in the test scripts only.
- Next step: run `run_dia.py` on a GPU host (any CUDA GPU with ≥8 GB VRAM;
  Dia needs ~4.4 GB at fp16 per its own benchmarks) with his 14.7 s Urdu
  note as audio prompt. If SIM ≥ 0.80 and the Urdu is intelligible, Dia
  becomes the Urdu engine and the verdict flips to PASS.

## 7. Files (all under `~/workspace/xploclone-urdu-test/`, none in git)

- `deepspeak-v1/model.pt` (7.53 GB, SHA-256 verified), `model-slim.pt`
  (3.26 GB weights-only fp32), `model-slim-bf16.pt` (1.63 GB, used for the run)
- `codec-weights.pth` (410 MB, SHA-256 verified)
- `deepspeak/short-ur-script.wav` (5.84 s), `long-ur-script.wav` (16.24 s),
  `short-roman-urdu.wav` (3.68 s) — DeepSpeak samples in the test voice
- `piper/baseline-ur-script.wav` (3.36 s) — Piper fixed-voice baseline
- `dia-urdu-model/config.json` + `model.pth` (3.22 GB, SHA-256 verified)
- `run_deepspeak.py`, `run_dia.py`, `run_dia_diag.py`, `deepspeak-run.log`,
  `dia-run.log`, `dia-urdu-transcript.txt`
- Venvs: `~/.venvs/xploclone-urdu-test` (torch 2.15.0+cpu, transformers 5.22.1,
  Irodori runtime, dacvae, dia), `~/.venvs/xploclone-piper-test` (piper-tts)
- Reference voice used throughout (private, never in git):
  `workspace/xploclone-sample-test/his-voice/ref-14s.wav`
