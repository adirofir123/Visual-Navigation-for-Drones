"""Frame time sampling and nearest SRT cue."""

import pytest

from app.preprocessing.frame_sampler import NearestCueIndex, frame_index_at_time, samples_seconds
from app.telemetry.telemetry_schema import TelemetryRecord


def _rec(bi: int, s: float, e: float) -> TelemetryRecord:
    return TelemetryRecord(
        block_index=bi,
        start_time_raw="",
        end_time_raw="",
        start_time_seconds=s,
        end_time_seconds=e,
        raw_text="",
    )


def test_samples_seconds_monotonic_until_duration() -> None:
    xs = samples_seconds(duration_s=3.01, stride_s=1.0)
    assert xs[0] == pytest.approx(0.0)
    assert pytest.approx(xs[-1]) == 3.0


def test_frame_index_at_time_clamps_to_count() -> None:
    assert frame_index_at_time(10.0, fps=30.0, frame_count=100) == 99
    assert frame_index_at_time(10.0, fps=30.0, frame_count=50) == 49


def test_nearest_record_prefers_midpoint() -> None:
    r1 = _rec(1, 0.0, 0.1)
    r2 = _rec(2, 1.0, 1.1)
    r3 = _rec(3, 2.0, 2.1)
    recs = [r1, r2, r3]
    idx = NearestCueIndex.from_records(recs)
    by_block = {r.block_index: r for r in recs}
    assert idx.nearest_record(1.52, by_block).block_index == 2
    assert idx.nearest_record(0.92, by_block).block_index == 2
