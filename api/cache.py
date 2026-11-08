"""Identical-request audio cache (in-memory, per process).

Why: the same short line is often generated repeatedly (greetings,
test calls, retries). The model re-runs every time; caching the
*output* for an identical (voice_id, normalised text, format) avoids
that. This does NOT cache the reference embedding — the 0.1.7
Chatterbox API takes ``audio_prompt_path`` per generate() call and
exposes no embedding object to cache (see api/engine.py).

Bounds: TTL + max entries, oldest-first eviction. No audio is written
to disk. Cache is per-process and resets on restart. Disabled when
``XPLOCLONE_AUDIO_CACHE_TTL_S=0`` or ``MAX_ENTRIES=0``.
"""

from __future__ import annotations

import hashlib
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass


@dataclass
class CacheEntry:
    pcm16: bytes
    expires_at: float


class AudioCache:
    """Thread-safe LRU-ish cache keyed by a hash of the request."""

    def __init__(self, ttl_s: int = 3600, max_entries: int = 32) -> None:
        self.ttl_s = ttl_s
        self.max_entries = max_entries
        self._lock = threading.Lock()
        self._entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self.hits = 0
        self.misses = 0

    @staticmethod
    def key(voice_id: str, text: str, fmt: str, prosody: str = "") -> str:
        # prosody is a stable fragment (ProsodySettings.cache_fragment).
        # It MUST be part of the key: the same text in preset "natural"
        # vs "firm" is different audio, and returning the cached
        # "default" take for a "natural" request would be silent
        # wrong-style audio. Empty string keeps the old 3-arg call
        # shape working (tests, scripts) — it means "default prosody".
        raw = f"{voice_id}\n{fmt}\n{prosody}\n{text}".encode()
        return hashlib.sha256(raw).hexdigest()

    @property
    def enabled(self) -> bool:
        return self.ttl_s > 0 and self.max_entries > 0

    def get(self, key: str) -> bytes | None:
        if not self.enabled:
            return None
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self.misses += 1
                return None
            if entry.expires_at <= now:
                del self._entries[key]
                self.misses += 1
                return None
            self._entries.move_to_end(key)
            self.hits += 1
            return entry.pcm16

    def put(self, key: str, pcm16: bytes) -> None:
        if not self.enabled or not pcm16:
            return
        with self._lock:
            self._entries[key] = CacheEntry(pcm16=pcm16, expires_at=time.monotonic() + self.ttl_s)
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self.hits = 0
            self.misses = 0
