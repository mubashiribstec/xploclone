# XploClone — Cost sheet (Phase 0 deliverable, PLAN-v2 §11)

Date: 2026-10-30. Prices checked this date; re-check before buying —
cloud GPU prices move weekly and spot prices move hourly.

## Comparator: ElevenLabs API

- ElevenLabs v4 Turbo API: **$0.04 per 1,000 characters ≈ $0.034 per
  minute** of speech (PLAN-v2 §2.3/§9.1; ~850 chars ≈ 1 minute at
  ~150 wpm). This is the number the break-even uses — the *app* prices
  ($6/30 min ≈ $0.20/min Starter, $22/121 min ≈ $0.18/min Creator) are
  NOT the comparator for Xplogent, which would use the API.
- ElevenLabs cost is purely variable: $0 at zero usage, $0.034 × minutes.

## Cloud GPU prices (checked 2026-10-30)

| GPU (VRAM) | Provider / tier | $/hour | Source (date) |
|---|---|---|---|
| RTX 4090 (24 GB) | RunPod Community | **$0.34** | RunPod pricing, fetched 2026-10-30 |
| RTX 4090 (24 GB) | RunPod Secure Cloud | $0.74–$0.89 | RunPod pricing page Sep 2026; $0.89 in an Oct 26 2026 API check |
| RTX 4090 (24 GB) | Vast.ai spot | $0.34–$0.48 | Vast.ai marketplace, Oct 2026 guides |
| L4 (24 GB) | RunPod Pods | **$0.49** | RunPod pricing table, updated 27 Sep 2026 |
| A10 (24 GB) | Lambda Labs | $1.29 | Lambda pricing, verified Sep 2026 |
| A100 80 GB | RunPod / Lambda | $1.59–$1.89 | RunPod / Lambda, Sep–Oct 2026 |

Notes: prices exclude storage ($0.10/GB/mo RunPod) and, on some
providers, egress. Spot/community tiers can be pre-empted — do not use
them for live calls without the GPU-down fallback (Phase 3).
Recommended v1 prod pick (to confirm at Gate 1): **L4 or RTX 4090,
24 GB, on-demand/secure tier** — both exceed the ≥ 12 GB rule with
headroom for one Chatterbox Turbo engine (~4–6 GB VRAM).

## Break-even maths (honest version)

A GPU you rent by the hour is a *fixed* cost; ElevenLabs is *variable*.
XploClone wins only if you generate enough minutes, or if the GPU is
not left running idle.

**Always-on GPU (worst case — do not do this for low volume):**

| GPU | $/month (730 h) | Break-even minutes/month vs $0.034/min |
|---|---|---|
| L4 @ $0.49/h | $357.70 | 10,521 min (~175 h of speech) |
| RTX 4090 @ $0.74/h | $540.20 | 15,888 min (~265 h of speech) |

At, say, 600 min/month (ElevenLabs Pro-tier volume), ElevenLabs API
costs **$20.40/month**. An always-on GPU at $358+/month loses badly.
**Do not run an always-on GPU for low volume.**

**On-demand GPU (the actual v1 model):**
Chatterbox Turbo claims up to ~6× real-time synthesis (vendor claim,
UNVERIFIED on the prod GPU — measure at Gate 1). At 6×, 600 min of
speech needs ~100 min (1.7 h) of GPU time:

| GPU | GPU hours for 600 min speech | Cost |
|---|---|---|
| RTX 4090 community @ $0.34/h | ~1.7 h | **~$0.58** |
| L4 @ $0.49/h | ~1.7 h | **~$0.83** |
| RTX 4090 secure @ $0.74/h | ~1.7 h | **~$1.26** |

vs ElevenLabs API for the same 600 min: **$20.40**.
Even at 1× real-time (worst case, 10 h GPU): 4090 community = $3.40.

**Break-even rule of thumb (on-demand):** XploClone beats the ElevenLabs
API on cost whenever GPU-hours × $/h < minutes × $0.034. At $0.49/h and
6× real-time, that is true from the first minute. At 1× real-time, it
is true up to ~$2.04/min of GPU time — i.e. always, for any GPU under
~$2/h. The real cost driver is **idle time**, not synthesis time.

## What this means for the owner (decision needed)

1. **File generation / videos:** on-demand GPU (spin up, generate, shut
   down) — XploClone is ~20–35× cheaper than the ElevenLabs API at
   600 min/month. ✅
2. **Live Xplogent calls:** the GPU must be up during call hours, so
   idle time dominates. Cost it per *call-hour*, not per speech-minute,
   and compare against ElevenLabs' per-minute price *plus* the value of
   owning the voice. If call volume is low (< ~2,000 min/month),
   an always-on GPU may cost more than ElevenLabs — use scale-to-zero
   or keep ElevenLabs/Cartesia as the live-call voice until volume
   justifies a dedicated GPU. This is a Phase 3 decision, not a Phase 1
   assumption.
3. **Dev (Z640, GTX 1660 Super):** $0 marginal (already owned),
   dev-only, one engine at a time.

## Assumptions to verify at Gate 1 (do not trust until measured)

- [ ] Real synthesis speed (× real-time) on the chosen prod GPU.
- [ ] Model TTFA p50/p95 on the prod GPU (target p95 < 200 ms).
- [ ] Actual $/hour paid (spot vs on-demand, storage, egress).
