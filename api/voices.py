"""Voice registry — the ONLY voices XploClone will ever serve in v1.

Hardcoded by design (PLAN-v2 §2.1, §6.1). There is no endpoint to create a
voice, and no user-uploaded voices. Each voice is Mubashir Ali's own voice,
recorded with written + spoken consent (see docs/CONSENT.md).

- ``mubashir-en-us`` / ``mubashir-en-gb``: Chatterbox Turbo (MIT), committed.
- ``mubashir-ur``: engine TBD — gated Urdu spike (docs/URDU-SPIKE.md).
  Until the spike passes and an engine is loaded, this voice reports
  ``unavailable`` and POST /v1/tts returns 503 ``engine_unavailable``.
  It is NEVER silently served by the English engine or by a Hindi voice.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Voice:
    voice_id: str
    language: str  # BCP-47-ish code the API accepts; anything else is rejected.
    accent: str
    engine: str
    # "loaded" | "unavailable" — computed at runtime, not stored here.
    description: str


VOICES: tuple[Voice, ...] = (
    Voice(
        voice_id="mubashir-en-us",
        language="en-US",
        accent="US",
        engine="chatterbox-turbo",
        description="Mubashir Ali, English, US accent.",
    ),
    Voice(
        voice_id="mubashir-en-gb",
        language="en-GB",
        accent="GB",
        engine="chatterbox-turbo",
        description="Mubashir Ali, English, British accent.",
    ),
    Voice(
        voice_id="mubashir-ur",
        language="ur",
        accent="PK",
        engine="tbd-urdu-spike",
        description="Mubashir Ali, Urdu. Engine not committed — see docs/URDU-SPIKE.md.",
    ),
)

VOICE_IDS = frozenset(v.voice_id for v in VOICES)

ENGLISH_VOICE_IDS = frozenset({"mubashir-en-us", "mubashir-en-gb"})

URDU_VOICE_ID = "mubashir-ur"


def get_voice(voice_id: str) -> Voice | None:
    for voice in VOICES:
        if voice.voice_id == voice_id:
            return voice
    return None
