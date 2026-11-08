"""Rate-limit unit tests (api/rate_limit.py) — no HTTP, no GPU."""

import asyncio

from api.rate_limit import RateLimiter, SynthesisQueue


def test_rate_limiter_allows_up_to_limit() -> None:
    limiter = RateLimiter(per_min=3)
    assert limiter.allow("k")[0] is True
    assert limiter.allow("k")[0] is True
    assert limiter.allow("k")[0] is True
    allowed, retry_after = limiter.allow("k")
    assert allowed is False
    assert retry_after >= 1


def test_rate_limiter_is_per_key() -> None:
    limiter = RateLimiter(per_min=1)
    assert limiter.allow("a")[0] is True
    assert limiter.allow("a")[0] is False
    assert limiter.allow("b")[0] is True


def test_rate_limiter_window_expiry() -> None:
    limiter = RateLimiter(per_min=1, window_s=0.05)
    assert limiter.allow("k")[0] is True
    assert limiter.allow("k")[0] is False
    import time

    time.sleep(0.06)
    assert limiter.allow("k")[0] is True


def test_queue_rejects_when_full() -> None:
    async def _run() -> None:
        queue = SynthesisQueue(max_waiters=0, timeout_s=1.0)
        assert await queue.acquire() is False

    asyncio.run(_run())


def test_queue_serialises() -> None:
    async def _run() -> bool:
        queue = SynthesisQueue(max_waiters=5, timeout_s=0.2)
        first = await queue.acquire()
        assert first is True
        # Second acquire must wait for the first release (timeout proves it).
        second = await queue.acquire()
        queue.release()
        return first and second is False

    assert asyncio.run(_run()) is True
