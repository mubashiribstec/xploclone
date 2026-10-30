"""In-memory request metrics (v1 — no Prometheus server dependency).

Exposed at GET /metrics in Prometheus text format, plus the counters the
README promises: requests by voice_id/status, latency samples, characters
synthesised. Counters reset on restart; that is acceptable for v1 and is
documented in docs/BUILD-LOG.md. A persistent metrics store is Phase 5.
"""

from __future__ import annotations

import threading
import time
from collections import Counter, defaultdict


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.requests_total: Counter[str] = Counter()
        self.errors_total: Counter[str] = Counter()
        self.chars_total: Counter[str] = Counter()
        self.latency_ms: dict[str, list[float]] = defaultdict(list)
        self.started_at = time.time()

    def record(
        self,
        voice_id: str,
        status: str,
        latency_ms: float,
        chars: int = 0,
        error_code: str | None = None,
    ) -> None:
        with self._lock:
            self.requests_total[f"{voice_id}:{status}"] += 1
            self.chars_total[voice_id] += chars
            samples = self.latency_ms[voice_id]
            samples.append(latency_ms)
            if len(samples) > 1000:
                del samples[: len(samples) - 1000]
            if error_code:
                self.errors_total[f"{voice_id}:{error_code}"] += 1

    def _percentile(self, values: list[float], pct: float) -> float:
        # Linear interpolation (m18) — the old index lookup made p95
        # misleading on small samples.
        if not values:
            return 0.0
        ordered = sorted(values)
        if len(ordered) == 1:
            return ordered[0]
        rank = pct / 100.0 * (len(ordered) - 1)
        lo = int(rank)
        hi = min(lo + 1, len(ordered) - 1)
        frac = rank - lo
        return ordered[lo] * (1.0 - frac) + ordered[hi] * frac

    def render_prometheus(self) -> str:
        lines = [
            "# HELP xploclone_requests_total Requests by voice and status",
            "# TYPE xploclone_requests_total counter",
        ]
        with self._lock:
            for key, value in sorted(self.requests_total.items()):
                voice, status = key.split(":", 1)
                lines.append(
                    f'xploclone_requests_total{{voice_id="{voice}",status="{status}"}} {value}'
                )
            lines.append("# HELP xploclone_chars_total Characters synthesised by voice")
            lines.append("# TYPE xploclone_chars_total counter")
            for voice, value in sorted(self.chars_total.items()):
                lines.append(f'xploclone_chars_total{{voice_id="{voice}"}} {value}')
            lines.append("# HELP xploclone_latency_ms_p50 TTS latency p50 (ms)")
            lines.append("# TYPE xploclone_latency_ms_p50 gauge")
            for voice, samples in sorted(self.latency_ms.items()):
                p50 = self._percentile(samples, 50)
                p95 = self._percentile(samples, 95)
                lines.append(f'xploclone_latency_ms_p50{{voice_id="{voice}"}} {p50:.1f}')
                lines.append(f'xploclone_latency_ms_p95{{voice_id="{voice}"}} {p95:.1f}')
            lines.append("# HELP xploclone_errors_total Errors by voice and code")
            lines.append("# TYPE xploclone_errors_total counter")
            for key, value in sorted(self.errors_total.items()):
                voice, code = key.split(":", 1)
                lines.append(f'xploclone_errors_total{{voice_id="{voice}",code="{code}"}} {value}')
            lines.append(f"# uptime_seconds {time.time() - self.started_at:.1f}")
        return "\n".join(lines) + "\n"


METRICS = Metrics()
