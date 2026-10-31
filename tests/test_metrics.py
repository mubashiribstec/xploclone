"""Metrics tests — interpolated percentiles (m18)."""

from api.metrics import Metrics


def test_percentile_interpolates() -> None:
    m = Metrics()
    # p50 of [0, 100] is 50 by interpolation, not 100 by index lookup.
    assert m._percentile([0.0, 100.0], 50) == 50.0
    assert m._percentile([0.0, 100.0], 95) == 95.0
    assert m._percentile([10.0], 95) == 10.0
    assert m._percentile([], 95) == 0.0
    assert m._percentile([0.0, 10.0, 20.0, 30.0], 25) == 7.5
