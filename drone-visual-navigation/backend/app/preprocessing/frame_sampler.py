"""Video time sampling helpers and nearest SRT cue by midpoint time."""

from __future__ import annotations

import bisect
from dataclasses import dataclass

from app.telemetry.telemetry_schema import TelemetryRecord


def samples_seconds(*, duration_s: float, stride_s: float) -> list[float]:
    """Sample times ``0``, ``stride``, … up to ``duration`` (floating edge tolerant)."""

    if duration_s < 0 or stride_s <= 0:
        return []

    eps = 1e-9
    out: list[float] = []
    t = 0.0
    while t <= duration_s + eps:
        out.append(round(t, 6))
        t += stride_s
    return out


def frame_index_at_time(
    timestamp_seconds: float,
    fps: float,
    *,
    frame_count: int | None,
) -> int:
    idx = int(round(timestamp_seconds * fps))
    if frame_count is not None and frame_count > 0:
        idx = max(0, min(idx, frame_count - 1))
    else:
        idx = max(0, idx)
    return idx


@dataclass(frozen=True)
class NearestCueIndex:
    """Precomputed midpoint times for binary search."""

    mids: list[float]
    indices: list[int]

    @classmethod
    def from_records(cls, records: list[TelemetryRecord]) -> NearestCueIndex:
        pairs: list[tuple[float, int]] = []
        for r in records:
            mid = 0.5 * (r.start_time_seconds + r.end_time_seconds)
            pairs.append((mid, r.block_index))
        pairs.sort(key=lambda p: (p[0], p[1]))
        mids = [p[0] for p in pairs]
        indices = [p[1] for p in pairs]
        return cls(mids=mids, indices=indices)

    def nearest_record(self, t: float, by_block: dict[int, TelemetryRecord]) -> TelemetryRecord | None:
        """Pick cue with midpoint nearest to ``t``; ties → smaller ``block_index``."""

        if not self.mids:
            return None
        i = bisect.bisect_left(self.mids, t)
        candidates: list[int] = []
        if i < len(self.mids):
            candidates.append(i)
        if i > 0:
            candidates.append(i - 1)
        best_idx: int | None = None
        best_dist = float("inf")
        best_block = 1 << 30
        for ci in candidates:
            d = abs(self.mids[ci] - t)
            bi = self.indices[ci]
            if d < best_dist or (abs(d - best_dist) < 1e-12 and bi < best_block):
                best_dist = d
                best_block = bi
                best_idx = ci
        if best_idx is None:
            return None
        return by_block.get(self.indices[best_idx])
