"""Rate limiting + FIFO synthesis queue (PLAN-v2 §6.4).

- Rate limit: 60 requests/minute per API key (default, tunable via env).
  Sliding window, in-memory. Exceeding it returns 429 with Retry-After.
- Synthesis queue: max 1 concurrent synthesis on a single GPU in v1.
  Extra requests wait FIFO up to ``queue_max`` (default 10); beyond that,
  or after ``request_timeout_s`` (default 30 s) waiting, the request gets
  503 ``engine_busy`` with a Retry-After header. Never silent degradation.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque


class RateLimiter:
    """Sliding-window rate limiter, keyed by API-key hash."""

    def __init__(self, per_min: int = 60, window_s: float = 60.0) -> None:
        self.per_min = per_min
        self.window_s = window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds)."""
        now = time.monotonic()
        hits = self._hits[key]
        while hits and hits[0] <= now - self.window_s:
            hits.popleft()
        if len(hits) >= self.per_min:
            retry_after = int(self.window_s - (now - hits[0])) + 1
            return False, max(1, retry_after)
        hits.append(now)
        return True, 0


class SynthesisQueue:
    """FIFO gate: 1 synthesis at a time, bounded waiters, bounded wait."""

    def __init__(self, max_waiters: int = 10, timeout_s: float = 30.0) -> None:
        self._sem = asyncio.Semaphore(1)
        self._waiters = 0
        self.max_waiters = max_waiters
        self.timeout_s = timeout_s

    async def acquire(self) -> bool:
        """True if the slot was acquired, False if the queue is full."""
        if self._waiters >= self.max_waiters:
            return False
        self._waiters += 1
        try:
            await asyncio.wait_for(self._sem.acquire(), timeout=self.timeout_s)
            return True
        except TimeoutError:
            return False
        finally:
            self._waiters -= 1

    def release(self) -> None:
        self._sem.release()
