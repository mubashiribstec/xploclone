"""Prosody tests — presets, overrides, validation, engine pass-through.

No GPU, no torch: the engine's ``_turbo`` is a stub that records the
kwargs ``generate()`` was called with. These tests prove the *wiring*
— that the preset values reach the model call — not voice quality.
"""

from __future__ import annotations

import numpy as np
import pytest

from api.engine import EngineRegistry
from api.prosody import (
    PRESETS,
    TURBO_CFG_EFFECTIVE,
    TURBO_EXAGGERATION_EFFECTIVE,
    resolve_prosody,
)


def test_preset_values_match_skill() -> None:
    """Task values: natural 0.7/0.3, warm 0.6/0.4, firm 0.4/0.6, default 0.5/0.5."""
    assert (PRESETS["natural"].exaggeration, PRESETS["natural"].cfg_weight) == (0.7, 0.3)
    assert (PRESETS["warm"].exaggeration, PRESETS["warm"].cfg_weight) == (0.6, 0.4)
    assert (PRESETS["firm"].exaggeration, PRESETS["firm"].cfg_weight) == (0.4, 0.6)
    assert (PRESETS["default"].exaggeration, PRESETS["default"].cfg_weight) == (0.5, 0.5)


def test_natural_preset_raises_temperature() -> None:
    """The audible part on Turbo: natural uses a higher temperature
    than default (more variation, less metronomic delivery)."""
    assert PRESETS["natural"].temperature > PRESETS["default"].temperature
    assert PRESETS["firm"].temperature < PRESETS["default"].temperature


def test_resolve_defaults_to_default_preset() -> None:
    assert resolve_prosody().preset == "default"
    assert resolve_prosody(preset="natural").preset == "natural"


def test_style_is_an_alias_for_preset() -> None:
    assert resolve_prosody(style="warm") == resolve_prosody(preset="warm")


def test_explicit_knob_overrides_preset() -> None:
    resolved = resolve_prosody(preset="natural", temperature=0.85)
    assert resolved.exaggeration == 0.7  # preset kept
    assert resolved.cfg_weight == 0.3
    assert resolved.temperature == 0.85  # explicit wins


def test_unknown_preset_rejected() -> None:
    with pytest.raises(ValueError, match="unknown preset"):
        resolve_prosody(preset="dramatic")


def test_preset_style_conflict_rejected() -> None:
    with pytest.raises(ValueError, match="conflicts"):
        resolve_prosody(preset="natural", style="warm")


def test_out_of_range_knob_rejected() -> None:
    with pytest.raises(ValueError, match="out of range"):
        resolve_prosody(exaggeration=1.5)
    with pytest.raises(ValueError, match="out of range"):
        resolve_prosody(cfg_weight=-0.1)
    with pytest.raises(ValueError, match="out of range"):
        resolve_prosody(temperature=2.0)


def test_turbo_ignores_exaggeration_and_cfg() -> None:
    """Verified from the chatterbox-tts 0.1.7 wheel (see api/prosody.py):
    Turbo ignores both knobs. These flags must stay False — if a
    future chatterbox version honours them, update the flags AND the
    docs, do not just flip them."""
    assert TURBO_EXAGGERATION_EFFECTIVE is False
    assert TURBO_CFG_EFFECTIVE is False


def test_cache_fragment_differs_per_preset() -> None:
    """Same text + different preset must never share a cache entry."""
    natural = resolve_prosody(preset="natural").cache_fragment()
    firm = resolve_prosody(preset="firm").cache_fragment()
    default = resolve_prosody().cache_fragment()
    assert natural != firm != default
    assert resolve_prosody(preset="natural").cache_fragment() == natural


class _FakeTensor:
    """Minimal torch-tensor stand-in for _synthesise_one."""

    def __init__(self, values: np.ndarray) -> None:
        self._values = values

    def squeeze(self, dim: int) -> _FakeTensor:
        return self

    def detach(self) -> _FakeTensor:
        return self

    def cpu(self) -> _FakeTensor:
        return self

    def numpy(self) -> np.ndarray:
        return self._values


class _FakeTurbo:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def generate(self, text: str, **kwargs) -> _FakeTensor:  # type: ignore[no-untyped-def]
        self.calls.append({"text": text, **kwargs})
        return _FakeTensor(np.array([0.5, -0.5, 0.0], dtype=np.float32))


def test_engine_passes_prosody_to_generate() -> None:
    """Preset values must actually reach turbo.generate() — a preset
    that only lives in the API layer and never reaches the model is
    a fake control."""
    reg = EngineRegistry()
    fake = _FakeTurbo()
    reg._turbo = fake  # type: ignore[assignment]
    prosody = resolve_prosody(preset="natural")
    pcm = reg._synthesise_one("mubashir-en-gb", "Hello there.", prosody)
    assert len(pcm) > 0
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["text"] == "Hello there."
    assert call["exaggeration"] == 0.7
    assert call["cfg_weight"] == 0.3
    assert call["temperature"] == 0.9
    assert call["top_p"] == 0.95
    assert call["repetition_penalty"] == 1.2


def test_synthesize_result_records_prosody() -> None:
    """SynthesisResult carries the requested prosody + the honest
    effective flags, so nothing downstream can claim exaggeration
    or CFG changed the audio on Turbo."""
    reg = EngineRegistry()
    fake = _FakeTurbo()
    reg._turbo = fake  # type: ignore[assignment]
    reg._loaded = True
    reg.has_reference = lambda voice_id: True  # type: ignore[method-assign]
    prosody = resolve_prosody(preset="warm")
    result = reg.synthesize("mubashir-en-gb", ["Hello."], prosody)
    assert result.prosody.preset == "warm"
    assert result.exaggeration_effective is False
    assert result.cfg_effective is False
