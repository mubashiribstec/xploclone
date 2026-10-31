"""Prosody controls — human-voice presets for ``POST /v1/tts``.

Verified finding (chatterbox source, inspected 2026-10-30
on the 0.1.7 wheel and confirmed on git master 5de7a54, 2026-10-31):
``ChatterboxTurboTTS.generate()`` ACCEPTS ``exaggeration`` and
``cfg_weight`` as arguments, but Turbo IGNORES them:

- ``generate()`` warns "CFG, min_p and exaggeration are not supported
  by Turbo version and will be ignored."
- ``Turbo.from_local`` sets ``hp.emotion_adv = False``, so the
  conditioning encoder has no ``emotion_adv`` projection — the
  exaggeration value passed to ``prepare_conditionals`` is dead.
- ``inference_turbo`` hardcodes ``cfg_weight=0.0`` and never receives
  a cfg_weight argument.

The full (non-Turbo) ``ChatterboxTTS`` (500M) DOES honour both knobs
(``tts.py``: emotion_adv defaults on, CFG duplicates the text tokens
and passes cfg_weight to ``t3.inference``). That model is a Phase 2
candidate, not in this build.

So the API still accepts ``exaggeration`` / ``cfg_weight`` (validated,
logged, and passed to ``generate()`` so the call is future-proof if
the engine changes), but this module records them as NOT effective on
Turbo, and the presets get their audible variation from the sampling
knobs Turbo DOES honour: ``temperature``, ``top_p`` and
``repetition_penalty``. Never claim a preset changed exaggeration or
CFG on Turbo — the response headers say so explicitly.

Tuning procedure (skill: change one knob at a time, re-listen to the
SAME script): start from preset ``natural``; if the voice still sounds
flat, raise ``temperature`` one step (0.9 -> 1.0); if it sounds
unstable, lower it (0.9 -> 0.85). Do not change two knobs at once.
"""

from __future__ import annotations

from dataclasses import dataclass

# Turbo: verified from the chatterbox source (see module docstring).
# These are facts about the engine, not configuration.
TURBO_EXAGGERATION_EFFECTIVE = False
TURBO_CFG_EFFECTIVE = False


@dataclass(frozen=True)
class ProsodySettings:
    """Resolved prosody for one synthesis request.

    ``exaggeration`` / ``cfg_weight`` are the requested values (passed
    to ``generate()`` but ignored by Turbo — see above).
    ``temperature`` / ``top_p`` / ``top_k`` / ``repetition_penalty``
    are the knobs that actually vary Turbo output.
    """

    preset: str = "default"
    exaggeration: float = 0.5
    cfg_weight: float = 0.5
    temperature: float = 0.8
    top_p: float = 0.95
    top_k: int = 1000
    repetition_penalty: float = 1.2

    def cache_fragment(self) -> str:
        """Stable fragment for the audio-cache key (order matters)."""
        return (
            f"preset={self.preset}|ex={self.exaggeration:.2f}"
            f"|cfg={self.cfg_weight:.2f}|t={self.temperature:.2f}"
            f"|p={self.top_p:.2f}|k={self.top_k}|rp={self.repetition_penalty:.2f}"
        )


PRESETS: dict[str, ProsodySettings] = {
    # Skill's flat-voice fix: raise exaggeration to 0.7, lower CFG to
    # 0.3. On Turbo the audible part is temperature 0.9 (more
    # variation, less metronomic delivery).
    "natural": ProsodySettings(
        preset="natural",
        exaggeration=0.7,
        cfg_weight=0.3,
        temperature=0.9,
        top_p=0.95,
        top_k=1000,
        repetition_penalty=1.2,
    ),
    "warm": ProsodySettings(
        preset="warm",
        exaggeration=0.6,
        cfg_weight=0.4,
        temperature=0.85,
        top_p=0.95,
        top_k=1000,
        repetition_penalty=1.2,
    ),
    "firm": ProsodySettings(
        preset="firm",
        exaggeration=0.4,
        cfg_weight=0.6,
        temperature=0.75,
        top_p=0.90,
        top_k=1000,
        repetition_penalty=1.3,
    ),
    "default": ProsodySettings(
        preset="default",
        exaggeration=0.5,
        cfg_weight=0.5,
        temperature=0.8,
        top_p=0.95,
        top_k=1000,
        repetition_penalty=1.2,
    ),
}

PRESET_NAMES = tuple(PRESETS)

DEFAULT_PROSODY = PRESETS["default"]

# Hard ranges for explicit overrides (Pydantic enforces the same).
_RANGES: dict[str, tuple[float, float]] = {
    "exaggeration": (0.0, 1.0),
    "cfg_weight": (0.0, 1.0),
    "temperature": (0.1, 1.5),
    "top_p": (0.05, 1.0),
    "repetition_penalty": (1.0, 2.0),
}


def resolve_prosody(
    preset: str | None = None,
    style: str | None = None,
    exaggeration: float | None = None,
    cfg_weight: float | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    repetition_penalty: float | None = None,
) -> ProsodySettings:
    """Resolve preset + explicit overrides into one ProsodySettings.

    ``style`` is an alias for ``preset`` (web UI sends ``preset``;
    either may be used, but not two different values at once).
    Explicit knobs override the preset. Raises ValueError on an
    unknown preset, conflicting preset/style, or an out-of-range knob.
    """
    name = preset or style
    if preset is not None and style is not None and preset != style:
        raise ValueError(f"preset {preset!r} conflicts with style {style!r}")
    if name is None:
        name = "default"
    if name not in PRESETS:
        raise ValueError(f"unknown preset {name!r} (valid: {', '.join(PRESET_NAMES)})")

    overrides: dict[str, float] = {}
    for field, value in (
        ("exaggeration", exaggeration),
        ("cfg_weight", cfg_weight),
        ("temperature", temperature),
        ("top_p", top_p),
        ("repetition_penalty", repetition_penalty),
    ):
        if value is None:
            continue
        low, high = _RANGES[field]
        if not low <= value <= high:
            raise ValueError(f"{field} {value} out of range [{low}, {high}]")
        overrides[field] = value
    base = PRESETS[name]
    return ProsodySettings(
        preset=base.preset,
        exaggeration=overrides.get("exaggeration", base.exaggeration),
        cfg_weight=overrides.get("cfg_weight", base.cfg_weight),
        temperature=overrides.get("temperature", base.temperature),
        top_p=overrides.get("top_p", base.top_p),
        top_k=base.top_k,
        repetition_penalty=overrides.get("repetition_penalty", base.repetition_penalty),
    )
